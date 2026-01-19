import sys
import os
import pandas as pd
from datetime import datetime
import logging
import time
import json
from typing import Dict, List, Tuple, Optional

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PaperTrader import PaperTrader
from DataStream_Engine import DataStream
from DataStream_Engine.aggregator import TickAggregator
from Algorithms.sbin_sentinel_strategy import SbinSentinelStrategy
from Database import DatabaseConnection, TradeRepository 
from reporting_engine import ReportingEngine
from Backtesting.config import BacktestConfig
from Backtesting.data_fetcher import HistoricalDataFetcher
from login import get_kite_instance

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Single Stock Sentinel Configuration
SYMBOL = "SBIN"
INTERVAL_MIN = 5
LOOKBACK_WINDOW = 200 # Sufficient for EMA50 and VWAP

class SbinSentinelSession:
    def __init__(self):
        self.kite = get_kite_instance()
        self.history: Dict[str, pd.DataFrame] = {}
        self.instrument_token = None
        self.db = DatabaseConnection() 
        self.trade_repo = TradeRepository(self.db) 
        self.reporter = ReportingEngine()
        self.current_date_str = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Initializing Phase 40: SBIN SENTINEL SESSION")
        
        # Init Strategy
        self.strategy = SbinSentinelStrategy(params={'bias': 'LONG'})
        
        # Init components
        self.trader = PaperTrader(self.strategy, initial_capital=BacktestConfig.INITIAL_CAPITAL, trade_repo=self.trade_repo)
        self.aggregator = TickAggregator(interval_minutes=INTERVAL_MIN)
        
    def setup(self):
        # 1. Fetch initial history (Warmup)
        logger.info(f"Fetching warmup data for {SYMBOL}...")
        fetcher = HistoricalDataFetcher(self.kite)
        end_date = datetime.now()
        start_date = end_date - pd.Timedelta(days=15) # Sufficient for intraday indicators
        
        df = fetcher.fetch_historical_data(SYMBOL, start_date, end_date, interval=f"{INTERVAL_MIN}min")
        if not df.empty:
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            self.history[SYMBOL] = df.tail(LOOKBACK_WINDOW)
            logger.info(f"Loaded {len(df)} bars for {SYMBOL}")
        else:
            logger.error(f"Failed to fetch history for {SYMBOL}")
            sys.exit(1)
                
        # 2. Database Maintenance
        self.db.prune_old_data(days=120)
                
        # 3. Get Instrument Token
        instruments = self.kite.instruments("NSE")
        for inst in instruments:
            if inst['tradingsymbol'] == SYMBOL:
                self.instrument_token = inst['instrument_token']
                break
                
        if not self.instrument_token:
            logger.error(f"Token not found for {SYMBOL}")
            sys.exit(1)
            
        logger.info(f"Token mapped for {SYMBOL}: {self.instrument_token}")
        
    def run(self):
        self.setup()
        
        # Use existing access token
        with open("access_token.txt", "r") as f:
            access_token = f.read().strip()
            
        stream = DataStream(self.kite.api_key, access_token) 
        
        # Subscribe
        stream.subscribe([self.instrument_token])
        
        # Connect Callbacks
        stream.add_callback(self.on_tick)
        self.aggregator.add_callback(self.on_candle_closed)
        
        logger.info(f"SENTINEL ONLINE: Monitoring {SYMBOL}...")
        stream.start()
        
        try:
            while True:
                time.sleep(30)
                # Check for day change
                now_str = datetime.now().strftime('%Y-%m-%d')
                if now_str != self.current_date_str:
                    self.reporter.generate_daily_report(self.current_date_str)
                    self.current_date_str = now_str

                status = self.trader.get_status()
                logger.info(f"SBIN PnL: {status['total_value'] - BacktestConfig.INITIAL_CAPITAL:.2f} | Pos: {len(status['portfolio']['positions'])}")
        except KeyboardInterrupt:
            logger.info("Stopping Sentinel...")
            self.reporter.generate_daily_report(self.current_date_str)
            stream.stop()

    def on_tick(self, tick):
        # Update current price in real-time for exit/monitoring
        if isinstance(tick, list):
            self.aggregator.on_tick(tick)
            for t in tick:
                if t.get('instrument_token') == self.instrument_token:
                    self.trader.current_prices[SYMBOL] = t.get('last_price')
        else:
            self.aggregator.on_tick([tick])
            if tick.get('instrument_token') == self.instrument_token:
                self.trader.current_prices[SYMBOL] = tick.get('last_price')

    def on_candle_closed(self, token, candle):
        if token != self.instrument_token: return
            
        if candle.index.tz is not None:
            candle.index = candle.index.tz_localize(None)
            
        # Update History
        if SYMBOL not in self.history:
            self.history[SYMBOL] = candle
        else:
            self.history[SYMBOL] = pd.concat([self.history[SYMBOL], candle])
            self.history[SYMBOL] = self.history[SYMBOL][~self.history[SYMBOL].index.duplicated(keep='last')]
        
        # Trim
        self.history[SYMBOL] = self.history[SYMBOL].iloc[-LOOKBACK_WINDOW:]
             
        self.run_strategy()

    def run_strategy(self):
        try:
            data_map = {SYMBOL: self.history[SYMBOL]}
            current_equity = self.trader.get_status()['total_value']
            existing_pos = list(self.trader.portfolio.get_positions().keys())
            
            signals = self.strategy.generate_signals(
                data_map, 
                datetime.now(), 
                capital=current_equity,
                existing_positions=existing_pos
            )
            
            if signals:
                logger.info(f"SENTINEL SIGNAL: {signals}")
                self.trader.process_signals(signals)
            
        except Exception as e:
            logger.error(f"Strategy Error: {e}")

if __name__ == "__main__":
    session = SbinSentinelSession()
    session.run()
