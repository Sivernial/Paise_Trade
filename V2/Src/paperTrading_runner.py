import sys
import os
import pandas as pd
from datetime import datetime
import logging
import time

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PaperTrader import PaperTrader
from DataStream_Engine import DataStream
from DataStream_Engine.aggregator import TickAggregator
from Algorithms import PairTradingStrategy
from Backtesting.config import BacktestConfig, StrategyConfig
from Backtesting.data_fetcher import HistoricalDataFetcher
from login import get_kite_instance

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Use Pair Config from StrategyConfig
PAIR = StrategyConfig.PAIR_TRADING['pairs'][0] # Use first pair e.g. ('ACC', 'AMBUJACEM')
SYMBOLS = list(PAIR)
INTERVAL_MIN = 15
LOOKBACK_WINDOW = StrategyConfig.PAIR_TRADING['lookback_window']

class PaperRunningSession:
    def __init__(self):
        self.kite = get_kite_instance()
        self.history: Dict[str, pd.DataFrame] = {}
        self.token_map = {} 
        self.reverse_token_map = {}
        
        # Init components
        # Init components
        strategy_params = {
            'pairs': [PAIR],
            'z_score_threshold': StrategyConfig.PAIR_TRADING['z_score_threshold'],
            'lookback_window': LOOKBACK_WINDOW,
            'stop_loss_z': StrategyConfig.PAIR_TRADING.get('stop_loss_z', 4.0),
            'take_profit_z': StrategyConfig.PAIR_TRADING.get('take_profit_z', 0.0)
        }
        self.strategy = PairTradingStrategy(params=strategy_params)
        self.trader = PaperTrader(self.strategy, initial_capital=BacktestConfig.INITIAL_CAPITAL)
        self.aggregator = TickAggregator(interval_minutes=INTERVAL_MIN)
        
    def setup(self):
        # 1. Fetch initial history (Warmup)
        logger.info("Fetching warmup data...")
        fetcher = HistoricalDataFetcher(self.kite)
        end_date = datetime.now()
        start_date = end_date - pd.Timedelta(days=10) # Enough for 60 bars
        
        for symbol in SYMBOLS:
            df = fetcher.fetch_historical_data(symbol, start_date, end_date, interval=f"{INTERVAL_MIN}min")
            if not df.empty:
                self.history[symbol] = df.tail(LOOKBACK_WINDOW + 10) # Keep buffer
                logger.info(f"Loaded {len(df)} bars for {symbol}")
            else:
                logger.error(f"Failed to fetch history for {symbol}")
                sys.exit(1)
                
        # 2. Get Instrument Tokens
        instruments = self.kite.instruments("NSE")
        for inst in instruments:
            if inst['tradingsymbol'] in SYMBOLS:
                self.token_map[inst['instrument_token']] = inst['tradingsymbol']
                self.reverse_token_map[inst['tradingsymbol']] = inst['instrument_token']
                
        logger.info(f"Tokens: {self.token_map}")
        
    def run(self):
        self.setup()
        
        # Setup Stream
        api_key = os.getenv("API_KEY", "") # Or from file
        with open("access_token.txt", "r") as f:
            access_token = f.read().strip()
            
        stream = DataStream(self.kite.api_key, access_token) # Kite instance has api_key
        
        # Subscribe
        tokens = list(self.token_map.keys())
        stream.subscribe(tokens)
        
        # Connect Callbacks
        stream.add_callback(self.on_tick)
        self.aggregator.add_callback(self.on_candle_closed)
        
        logger.info(f"Starting Paper Trading for {PAIR}")
        stream.start()
        
        try:
            while True:
                time.sleep(10)
                status = self.trader.get_status()
                logger.info(f"Portfolio: Rs {status['total_value']:.2f} | Open Pos: {status['portfolio']['positions']}")
        except KeyboardInterrupt:
            logger.info("Stopping...")
            stream.stop()

    def on_tick(self, tick):
        # Pass to aggregator
        # Tick might be single dict or list
        if isinstance(tick, list):
            self.aggregator.on_tick(tick)
        else:
            self.aggregator.on_tick([tick])
            
        # Also update current price in trader for MTM
        if isinstance(tick, list):
             for t in tick:
                 token = t.get('instrument_token')
                 price = t.get('last_price')
                 symbol = self.token_map.get(token)
                 if symbol:
                     self.trader.current_prices[symbol] = price

    def on_candle_closed(self, token_or_symbol, candle):
        # Aggregator might pass token if it doesn't know symbol. 
        # Our Aggregator implementation blindly passes what it gets.
        # But wait, Aggregator logic used 'instrument_token' from tick.
        # So 'token_or_symbol' is likely token.
        
        symbol = self.token_map.get(token_or_symbol)
        if not symbol:
            logger.warning(f"Unknown token {token_or_symbol}")
            return
            
        logger.info(f"New Candle {symbol}: {candle.iloc[-1]['close']}")
        
        # Update History
        if symbol not in self.history:
            self.history[symbol] = candle
        else:
            self.history[symbol] = pd.concat([self.history[symbol], candle])
        
        # Trim
        if len(self.history[symbol]) > LOOKBACK_WINDOW * 2:
             self.history[symbol] = self.history[symbol].iloc[-LOOKBACK_WINDOW:]
             
        # Check if we have fresh data for BOTH pairs to run strategy
        # Ideally, we wait for both bars to close. 
        # For now, run strategy on every bar close, it will use latest available data for both.
        
        self.run_strategy()

    def run_strategy(self):
        # Extract series
        try:
            data_map = {s: self.history[s]['close'] for s in SYMBOLS}
            
            # Run strategy
            # Note: generate_signals might expect data aligned by index. 
            # In live, indices (timestamps) should mostly match.
            signals = self.strategy.generate_signals(data_map, datetime.now())
            
            # Log Strategy State for Dashboard
            if hasattr(self.strategy, 'latest_state'):
                for pair_key, state in self.strategy.latest_state.items():
                    pair_str = f"{pair_key[0]}-{pair_key[1]}"
                    logger.info(
                        f"Strategy State for {pair_str}: "
                        f"Z-Score={state['z_score']:.2f}, "
                        f"Beta={state['beta']:.2f}, "
                        f"Spread={state['spread']:.2f}, "
                        f"AI Confidence={state.get('ai_confidence', 0.0):.2f}, "
                        f"Signal={'SIGNAL' if signals else 'NONE'}"
                    )
            
            if signals:
                logger.info(f"Signals generated: {signals}")
                self.trader.process_signals(signals)
                
        except Exception as e:
            logger.error(f"Strategy Error: {e}")

if __name__ == "__main__":
    session = PaperRunningSession()
    session.run()

