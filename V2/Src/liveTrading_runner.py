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
from Database.connection import DatabaseConnection
from Database.trade_repository import TradeRepository
from Common.notifier import notifier
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
        # Database
        self.db = DatabaseConnection()
        self.trade_repo = TradeRepository(self.db)
        
        # --- DYNAMIC PAIR SCANNING ---
        logger.info("⚡️ Running Dynamic Pair Scanner...")
        self.pairs = []
        try:
            from Common.pair_scanner import scan_pairs
            scanned_df = scan_pairs(days=60)
            
            if scanned_df is not None and not scanned_df.empty:
                count = 0
                for _, row in scanned_df.iterrows():
                    if count >= 4: break
                    self.pairs.append((row['Asset A'], row['Asset B']))
                    count += 1
                logger.info(f"✅ Selected Dynamic Pairs: {self.pairs}")
        except Exception as e:
            logger.error(f"Scanner Failed: {e}")
            
        if not self.pairs:
             logger.warning("Falling back to Config Pairs")
             self.pairs = StrategyConfig.PAIR_TRADING['pairs']

        # Update Global SYMBOLS based on dynamic pairs
        global SYMBOLS
        unique_syms = set()
        for p in self.pairs:
            unique_syms.add(p[0])
            unique_syms.add(p[1])
        SYMBOLS = list(unique_syms)
        logger.info(f"Active Symbols: {SYMBOLS}")
        
        strategy_params = {
            'pairs': self.pairs,
            'z_score_threshold': StrategyConfig.PAIR_TRADING['z_score_threshold'],
            'lookback_window': LOOKBACK_WINDOW,
            'stop_loss_z': StrategyConfig.PAIR_TRADING.get('stop_loss_z', 4.0),
            'take_profit_z': StrategyConfig.PAIR_TRADING.get('take_profit_z', 0.0)
        }
        self.strategy = PairTradingStrategy(params=strategy_params)
        
        # CRITICAL: Re-initialize internal state (pairs list and KF registry)
        self.strategy.pairs = self.pairs
        self.strategy.kf_registry = {}
        from Common.quant_utils import KalmanFilterReg
        for pair in self.pairs:
            self.strategy.kf_registry[pair] = KalmanFilterReg(delta=1e-4, R=1e-3)
            
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
        
        # Join pairs for display
        pair_disp = ", ".join([f"{p[0]}-{p[1]}" for p in self.pairs])
        logger.info(f"Starting LIVE Trading for {pair_disp}")
        stream.start()
        
        try:
            while True:
                time.sleep(10)
                status = self.trader.get_status()
                # logger.info(f"Live Status - Pos: {status['positions']}") # Reduce console spam
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
                    self.trade_repo.log_strategy_state(
                        pair_str,
                        state['z_score'],
                        state['beta'],
                        state['spread'],
                        state.get('ai_confidence', 0.0),
                        'SIGNAL' if signals else 'NONE'
                    )
            
            if signals:
                logger.info(f"Signals: {signals}")
                notifier.send(f"New Signal for {PAIR}: {signals}") # Send Alert
                
                # Process
                self.trader.process_signals(signals)
                
                # Check for closed trades (Naive check for illustration)
                # Ideally LiveTrader returns executed trade info
                # Here we just log signal generation
                
        except Exception as e:
            msg = f"Strategy Error: {e}"
            logger.error(msg)
            notifier.send(msg)

if __name__ == "__main__":
    session = LiveRunningSession()
    session.run()

