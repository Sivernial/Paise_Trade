import sys
import os
import pandas as pd
from datetime import datetime
import logging
import time

# Add parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from LiveTrader import LiveTrader
from DataStream_Engine import DataStream
from DataStream_Engine.aggregator import TickAggregator
from Algorithms import PairTradingStrategy
from Backtesting.config import BacktestConfig, StrategyConfig
from Backtesting.data_fetcher import HistoricalDataFetcher
from login import get_kite_instance

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Config
PAIR = StrategyConfig.PAIR_TRADING['pairs'][0]
SYMBOLS = list(PAIR)
INTERVAL_MIN = 15
LOOKBACK_WINDOW = StrategyConfig.PAIR_TRADING['lookback_window']

class LiveRunningSession:
    def __init__(self):
        logger.info("=" * 60)
        logger.info("WARNING: LIVE TRADING MODE")
        logger.info("This will execute REAL trades with REAL money!")
        logger.info("=" * 60)
        
        confirmation = input("Type 'YES' to confirm live trading: ")
        if confirmation != "YES":
            logger.info("Live trading cancelled")
            sys.exit(0)
            
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
        self.trader = LiveTrader(self.kite, self.strategy) # LiveTrader takes kite + strategy
        self.aggregator = TickAggregator(interval_minutes=INTERVAL_MIN)
        
    def setup(self):
        # 1. Fetch Warmup
        logger.info("Fetching warmup data...")
        fetcher = HistoricalDataFetcher(self.kite)
        end_date = datetime.now()
        start_date = end_date - pd.Timedelta(days=10) 
        
        for symbol in SYMBOLS:
            df = fetcher.fetch_historical_data(symbol, start_date, end_date, interval=f"{INTERVAL_MIN}min")
            if not df.empty:
                self.history[symbol] = df.tail(LOOKBACK_WINDOW + 10)
                logger.info(f"Loaded {len(df)} bars for {symbol}")
            else:
                logger.error(f"Failed to fetch history for {symbol}")
                sys.exit(1)
                
        # 2. Map Tokens
        instruments = self.kite.instruments("NSE")
        for inst in instruments:
            if inst['tradingsymbol'] in SYMBOLS:
                self.token_map[inst['instrument_token']] = inst['tradingsymbol']
                
        logger.info(f"Tokens: {self.token_map}")
        
    def run(self):
        self.setup()
        
        api_key = os.getenv("API_KEY", "")
        with open("access_token.txt", "r") as f:
            access_token = f.read().strip()
            
        stream = DataStream(self.kite.api_key, access_token)
        stream.subscribe(list(self.token_map.keys()))
        
        stream.add_callback(self.on_tick)
        self.aggregator.add_callback(self.on_candle_closed)
        
        logger.info(f"Starting LIVE Trading for {PAIR}")
        stream.start()
        
        try:
            while True:
                time.sleep(10)
                status = self.trader.get_status()
                logger.info(f"Live Status - Pos: {status['positions']}")
        except KeyboardInterrupt:
            logger.info("Stopping...")
            stream.stop()

    def on_tick(self, tick):
        if isinstance(tick, list):
            self.aggregator.on_tick(tick)
            for t in tick:
                 token = t.get('instrument_token')
                 price = t.get('last_price')
                 symbol = self.token_map.get(token)
                 if symbol:
                     self.trader.current_prices[symbol] = price
        else:
             self.aggregator.on_tick([tick])

    def on_candle_closed(self, token_or_symbol, candle):
        symbol = self.token_map.get(token_or_symbol)
        if not symbol: return
        
        logger.info(f"New Candle {symbol}: {candle.iloc[-1]['close']}")
        
        if symbol not in self.history:
            self.history[symbol] = candle
        else:
             self.history[symbol] = pd.concat([self.history[symbol], candle])
        
        if len(self.history[symbol]) > LOOKBACK_WINDOW * 2:
             self.history[symbol] = self.history[symbol].iloc[-LOOKBACK_WINDOW:]
             
        self.run_strategy()

    def run_strategy(self):
        try:
            data_map = {s: self.history[s]['close'] for s in SYMBOLS}
            signals = self.strategy.generate_signals(data_map, datetime.now())
            
            if signals:
                logger.info(f"Signals: {signals}")
                self.trader.process_signals(signals)
        except Exception as e:
            logger.error(f"Strategy Error: {e}")

if __name__ == "__main__":
    session = LiveRunningSession()
    session.run()

