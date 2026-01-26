import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import logging
import time
import argparse

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PaperTrader import PaperTrader
from DataStream_Engine import DataStream
from DataStream_Engine.aggregator import TickAggregator
from Algorithms.generic_3tf_strategy import Generic3TFStrategy
from Database import DatabaseConnection, TradeRepository 
from reporting_engine import ReportingEngine
from Backtesting.config import BacktestConfig
from Backtesting.data_fetcher import HistoricalDataFetcher
from Src.login import get_kite_instance
from config_3tf import CONFIG

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Generic3TFSession:
    def __init__(self, symbol: str):
        self.symbol = symbol.upper()
        if self.symbol not in CONFIG:
            raise ValueError(f"Symbol {self.symbol} not found in config_3tf.py")
            
        self.config = CONFIG[self.symbol]
        self.kite = get_kite_instance()
        self.history_10m: pd.DataFrame = None
        self.history_30m: pd.DataFrame = None
        self.history_1h: pd.DataFrame = None
        self.instrument_token = None
        self.db = DatabaseConnection() 
        self.trade_repo = TradeRepository(self.db) 
        self.reporter = ReportingEngine()
        self.current_date_str = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Initializing 3-TIMEFRAME MTFA SESSION for {self.symbol}")
        
        # Init Strategy with config params
        params = self.config['strategy_params'].copy()
        params['symbol'] = self.symbol
        self.strategy = Generic3TFStrategy(params=params)
        
        # Init Trader
        self.trader = PaperTrader(self.strategy, initial_capital=BacktestConfig.INITIAL_CAPITAL, trade_repo=self.trade_repo)
        
        # Triple Aggregators
        self.agg_10m = TickAggregator(interval_minutes=10)
        self.agg_30m = TickAggregator(interval_minutes=30)
        self.agg_1h = TickAggregator(interval_minutes=60)
        
    def setup(self):
        logger.info(f"Fetching MTFA warmup data for {self.symbol}...")
        fetcher = HistoricalDataFetcher(self.kite)
        end_date = datetime.now()
        lookbacks = self.config['lookbacks']
        
        # 1. Warmup 10m
        start_10m = end_date - timedelta(days=5)
        df_10m = fetcher.fetch_historical_data(self.symbol, start_10m, end_date, interval="10minute")
        if not df_10m.empty:
            if df_10m.index.tz: df_10m.index = df_10m.index.tz_localize(None)
            self.history_10m = df_10m.tail(lookbacks['10m'])
            logger.info(f"Loaded {len(self.history_10m)} 10m bars")
            
        # 2. Warmup 30m
        start_30m = end_date - timedelta(days=10)
        df_30m = fetcher.fetch_historical_data(self.symbol, start_30m, end_date, interval="30minute")
        if not df_30m.empty:
            if df_30m.index.tz: df_30m.index = df_30m.index.tz_localize(None)
            self.history_30m = df_30m.tail(lookbacks['30m'])
            logger.info(f"Loaded {len(self.history_30m)} 30m bars")
            
        # 3. Warmup 1h
        start_1h = end_date - timedelta(days=20)
        df_1h = fetcher.fetch_historical_data(self.symbol, start_1h, end_date, interval="60minute")
        if not df_1h.empty:
            if df_1h.index.tz: df_1h.index = df_1h.index.tz_localize(None)
            self.history_1h = df_1h.tail(lookbacks['1h'])
            logger.info(f"Loaded {len(self.history_1h)} 1h bars")
            
        # 4. Token Mapping
        instruments = self.kite.instruments("NSE")
        for inst in instruments:
            if inst['tradingsymbol'] == self.symbol:
                self.instrument_token = inst['instrument_token']
                break
        
        if not self.instrument_token:
            logger.error(f"Token not found for {self.symbol}")
            sys.exit(1)
            
        logger.info(f"Token: {self.instrument_token}")

    def run(self):
        self.setup()
        
        with open("access_token.txt", "r") as f:
            access_token = f.read().strip()
            
        stream = DataStream(self.kite.api_key, access_token)
        stream.subscribe([self.instrument_token])
        stream.add_callback(self.on_tick)
        
        self.agg_10m.add_callback(self.on_10m_closed)
        self.agg_30m.add_callback(self.on_30m_closed)
        self.agg_1h.add_callback(self.on_1h_closed)
        
        logger.info(f"3TF MTFA ONLINE: Monitoring {self.symbol}")
        stream.start()
        
        try:
            while True:
                time.sleep(30)
                status = self.trader.get_status()
                pnl = status['total_value'] - BacktestConfig.INITIAL_CAPITAL
                logger.info(f"{self.symbol} PnL: ₹{pnl:.2f} | Pos: {len(status['portfolio']['positions'])}")
        except KeyboardInterrupt:
            logger.info(f"Stopping {self.symbol} MTFA Session...")
            stream.stop()

    def on_tick(self, tick):
        if isinstance(tick, list):
            self.agg_10m.on_tick(tick)
            self.agg_30m.on_tick(tick)
            self.agg_1h.on_tick(tick)
            for t in tick:
                if t.get('instrument_token') == self.instrument_token:
                    self.trader.current_prices[self.symbol] = t.get('last_price')
            self.trader.check_security()
        else:
            self.agg_10m.on_tick([tick])
            self.agg_30m.on_tick([tick])
            self.agg_1h.on_tick([tick])
            if tick.get('instrument_token') == self.instrument_token:
                self.trader.current_prices[self.symbol] = tick.get('last_price')
            self.trader.check_security()

    def on_10m_closed(self, token, candle):
        if token != self.instrument_token: return
        if candle.index.tz: candle.index = candle.index.tz_localize(None)
        
        if self.history_10m is None: self.history_10m = candle
        else:
            self.history_10m = pd.concat([self.history_10m, candle])
            self.history_10m = self.history_10m[~self.history_10m.index.duplicated(keep='last')]
        
        self.history_10m = self.history_10m.iloc[-self.config['lookbacks']['10m']:]
        self.run_strategy()

    def on_30m_closed(self, token, candle):
        if token != self.instrument_token: return
        if candle.index.tz: candle.index = candle.index.tz_localize(None)
        
        if self.history_30m is None: self.history_30m = candle
        else:
            self.history_30m = pd.concat([self.history_30m, candle])
            self.history_30m = self.history_30m[~self.history_30m.index.duplicated(keep='last')]
        
        self.history_30m = self.history_30m.iloc[-self.config['lookbacks']['30m']:]
        logger.info(f"{self.symbol} 30m Candle Closed: {candle['close'].iloc[-1]:.2f}")

    def on_1h_closed(self, token, candle):
        if token != self.instrument_token: return
        if candle.index.tz: candle.index = candle.index.tz_localize(None)
        
        if self.history_1h is None: self.history_1h = candle
        else:
            self.history_1h = pd.concat([self.history_1h, candle])
            self.history_1h = self.history_1h[~self.history_1h.index.duplicated(keep='last')]
            
        self.history_1h = self.history_1h.iloc[-self.config['lookbacks']['1h']:]
        logger.info(f"{self.symbol} 1h Candle Closed: {candle['close'].iloc[-1]:.2f}")

    def run_strategy(self):
        if self.history_10m is None or self.history_30m is None or self.history_1h is None: return
        try:
            data_map = {
                self.symbol: {
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
                logger.info(f"{self.symbol} SIGNAL Triggered: {signals}")
                self.trader.process_signals(signals)
        except Exception as e:
            logger.error(f"Strategy Error ({self.symbol}): {e}", exc_info=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generic 3TF Paper Runner')
    parser.add_argument('--symbol', type=str, required=True, help='Trading symbol (e.g. ITC, INDIGO, SILVERBEES)')
    args = parser.parse_args()
    
    session = Generic3TFSession(args.symbol)
    session.run()
