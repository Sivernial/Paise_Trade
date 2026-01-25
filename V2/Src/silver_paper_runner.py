import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import logging
import time

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PaperTrader import PaperTrader
from DataStream_Engine import DataStream
from DataStream_Engine.aggregator import TickAggregator
from Algorithms.silver_sentinel_3tf_strategy import SilverSentinel3TFStrategy
from Database import DatabaseConnection, TradeRepository 
from reporting_engine import ReportingEngine
from Backtesting.config import BacktestConfig
from Backtesting.data_fetcher import HistoricalDataFetcher
from login import get_kite_instance

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SYMBOL = "SILVERBEES"
LOOKBACK_10M = 110
LOOKBACK_30M = 60
LOOKBACK_1H = 50

class SilverSentinelSession:
    def __init__(self):
        self.kite = get_kite_instance()
        self.history_10m: pd.DataFrame = None
        self.history_30m: pd.DataFrame = None
        self.history_1h: pd.DataFrame = None
        self.instrument_token = None
        self.db = DatabaseConnection() 
        self.trade_repo = TradeRepository(self.db) 
        self.reporter = ReportingEngine()
        self.current_date_str = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Initializing Phase 52: SILVER SENTINEL 3-TIMEFRAME MTFA SESSION")
        
        # Init Strategy with 3TF Parameters
        self.strategy = SilverSentinel3TFStrategy(params={
            'leverage': 4.0,
            'max_capital': 40000,
            'opening_noise_mins': 5,
            'profit_target': 0.005,
            'stop_loss': 0.0025,
            'sky_ema': 20,
            'forest_ema': 9,
            'tree_ema': 9
        })
        
        # Init Trader
        self.trader = PaperTrader(self.strategy, initial_capital=BacktestConfig.INITIAL_CAPITAL, trade_repo=self.trade_repo)
        
        # Triple Aggregators
        self.agg_10m = TickAggregator(interval_minutes=10)
        self.agg_30m = TickAggregator(interval_minutes=30)
        self.agg_1h = TickAggregator(interval_minutes=60)
        
    def setup(self):
        logger.info(f"Fetching MTFA warmup data for {SYMBOL}...")
        fetcher = HistoricalDataFetcher(self.kite)
        end_date = datetime.now()
        
        # 1. Warmup 10m
        start_10m = end_date - timedelta(days=5)
        df_10m = fetcher.fetch_historical_data(SYMBOL, start_10m, end_date, interval="10minute")
        if not df_10m.empty:
            if df_10m.index.tz: df_10m.index = df_10m.index.tz_localize(None)
            self.history_10m = df_10m.tail(LOOKBACK_10M)
            logger.info(f"Loaded {len(self.history_10m)} 10m bars")
            
        # 2. Warmup 30m
        start_30m = end_date - timedelta(days=10)
        df_30m = fetcher.fetch_historical_data(SYMBOL, start_30m, end_date, interval="30minute")
        if not df_30m.empty:
            if df_30m.index.tz: df_30m.index = df_30m.index.tz_localize(None)
            self.history_30m = df_30m.tail(LOOKBACK_30M)
            logger.info(f"Loaded {len(self.history_30m)} 30m bars")
            
        # 3. Warmup 1h
        start_1h = end_date - timedelta(days=20)
        df_1h = fetcher.fetch_historical_data(SYMBOL, start_1h, end_date, interval="60minute")
        if not df_1h.empty:
            if df_1h.index.tz: df_1h.index = df_1h.index.tz_localize(None)
            self.history_1h = df_1h.tail(LOOKBACK_1H)
            logger.info(f"Loaded {len(self.history_1h)} 1h bars")
            
        # 3. Token Mapping
        instruments = self.kite.instruments("NSE")
        for inst in instruments:
            if inst['tradingsymbol'] == SYMBOL:
                self.instrument_token = inst['instrument_token']
                break
        
        if not self.instrument_token:
            logger.error(f"Token not found for {SYMBOL}")
            sys.exit(1)
            
        logger.info(f"Token: {self.instrument_token}")

    def run(self):
        self.setup()
        
        with open("access_token.txt", "r") as f:
            access_token = f.read().strip()
            
        stream = DataStream(self.kite.api_key, access_token)
        stream.subscribe([self.instrument_token])
        stream.add_callback(self.on_tick)
        
        # Callbacks for all aggregators
        self.agg_10m.add_callback(self.on_10m_closed)
        self.agg_30m.add_callback(self.on_30m_closed)
        self.agg_1h.add_callback(self.on_1h_closed)
        
        logger.info(f"SILVER 3TF MTFA ONLINE: Monitoring {SYMBOL}")
        stream.start()
        
        try:
            while True:
                time.sleep(30)
                status = self.trader.get_status()
                logger.info(f"SILVER PnL: ₹{status['total_value'] - BacktestConfig.INITIAL_CAPITAL:.2f} | Pos: {len(status['portfolio']['positions'])}")
        except KeyboardInterrupt:
            logger.info("Stopping Silver Sentinel...")
            stream.stop()

    def on_tick(self, tick):
        if isinstance(tick, list):
            self.agg_10m.on_tick(tick)
            self.agg_30m.on_tick(tick)
            self.agg_1h.on_tick(tick)
            for t in tick:
                if t.get('instrument_token') == self.instrument_token:
                    self.trader.current_prices[SYMBOL] = t.get('last_price')
            
            # Real-time Security Audit (SL/TP) on every tick
            self.trader.check_security()
        else:
            self.agg_10m.on_tick([tick])
            self.agg_30m.on_tick([tick])
            self.agg_1h.on_tick([tick])
            if tick.get('instrument_token') == self.instrument_token:
                self.trader.current_prices[SYMBOL] = tick.get('last_price')
                
            self.trader.check_security()

    def on_10m_closed(self, token, candle):
        if token != self.instrument_token: return
        if candle.index.tz: candle.index = candle.index.tz_localize(None)
        
        if self.history_10m is None: self.history_10m = candle
        else:
            self.history_10m = pd.concat([self.history_10m, candle])
            self.history_10m = self.history_10m[~self.history_10m.index.duplicated(keep='last')]
        
        self.history_10m = self.history_10m.iloc[-LOOKBACK_10M:]
        self.run_strategy()

    def on_30m_closed(self, token, candle):
        if token != self.instrument_token: return
        if candle.index.tz: candle.index = candle.index.tz_localize(None)
        
        if self.history_30m is None: self.history_30m = candle
        else:
            self.history_30m = pd.concat([self.history_30m, candle])
            self.history_30m = self.history_30m[~self.history_30m.index.duplicated(keep='last')]
        
        self.history_30m = self.history_30m.iloc[-LOOKBACK_30M:]
        logger.info(f"SILVER Forest Updated (30m): {candle['close'].iloc[-1]:.2f}")

    def on_1h_closed(self, token, candle):
        if token != self.instrument_token: return
        if candle.index.tz: candle.index = candle.index.tz_localize(None)
        
        if self.history_1h is None: self.history_1h = candle
        else:
            self.history_1h = pd.concat([self.history_1h, candle])
            self.history_1h = self.history_1h[~self.history_1h.index.duplicated(keep='last')]
            
        self.history_1h = self.history_1h.iloc[-LOOKBACK_1H:]
        logger.info(f"Forest Updated (1H): {candle['close'].iloc[-1]:.2f}")

    def run_strategy(self):
        if self.history_10m is None or self.history_30m is None or self.history_1h is None: return
        try:
            data_map = {
                SYMBOL: {
                    '10minute': self.history_10m,
                    '30minute': self.history_30m,
                    '1hour': self.history_1h
                }
            }
            equity = self.trader.get_status()['total_value']
            existing = list(self.trader.portfolio.get_positions().keys())
            
            signals = self.strategy.generate_signals(
                data_map, datetime.now(), capital=equity, existing_positions=existing
            )
            
            if signals:
                logger.info(f"MTFA SIGNAL Triggered: {signals}")
                self.trader.process_signals(signals)
        except Exception as e:
            logger.error(f"Strategy Error: {e}", exc_info=True)

if __name__ == "__main__":
    session = SilverSentinelSession()
    session.run()
