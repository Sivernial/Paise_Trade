import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import logging
import time
import argparse

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from LiveTrader import LiveTrader
from DataStream_Engine import DataStream
from DataStream_Engine.aggregator import TickAggregator
from Algorithms.generic_3tf_strategy import Generic3TFStrategy
from Backtesting.data_fetcher import HistoricalDataFetcher
from Src.login import get_kite_instance
from config_3tf import CONFIG

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GenericLiveSession:
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
        
        logger.info(f"Initializing LIVE 3-TIMEFRAME MTFA SESSION for {self.symbol}")
        
        # Init Strategy
        params = self.config['strategy_params'].copy()
        params['symbol'] = self.symbol
        self.strategy = Generic3TFStrategy(params=params)
        
        # Init LIVE Trader
        self.trader = LiveTrader(self.kite, self.strategy)
        
        # Triple Aggregators
        self.agg_10m = TickAggregator(interval_minutes=10)
        self.agg_30m = TickAggregator(interval_minutes=30)
        self.agg_1h = TickAggregator(interval_minutes=60)
        
    def setup(self):
        logger.info(f"Fetching LIVE MTFA warmup data for {self.symbol}...")
        fetcher = HistoricalDataFetcher(self.kite)
        end_date = datetime.now()
        lookbacks = self.config['lookbacks']
        
        # 1. Warmup
        self.history_10m = fetcher.fetch_historical_data(self.symbol, end_date - timedelta(days=5), end_date, interval="10minute").tail(lookbacks['10m'])
        self.history_30m = fetcher.fetch_historical_data(self.symbol, end_date - timedelta(days=10), end_date, interval="30minute").tail(lookbacks['30m'])
        self.history_1h = fetcher.fetch_historical_data(self.symbol, end_date - timedelta(days=20), end_date, interval="60minute").tail(lookbacks['1h'])
        
        for df in [self.history_10m, self.history_30m, self.history_1h]:
            if df is not None and not df.empty and df.index.tz:
                df.index = df.index.tz_localize(None)
                
        # 2. Token Mapping
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
        
        logger.info(f"LIVE 3TF MTFA ONLINE: Monitoring {self.symbol}")
        stream.start()
        
        try:
            while True:
                time.sleep(30)
                status = self.trader.get_status()
                logger.info(f"LIVE {self.symbol} Monitoring | Positions: {status['positions']}")
        except KeyboardInterrupt:
            logger.info("Stopping Session...")
            stream.stop()

    def on_tick(self, tick):
        if isinstance(tick, list):
            self.agg_10m.on_tick(tick)
            self.agg_30m.on_tick(tick)
            self.agg_1h.on_tick(tick)
            for t in tick:
                if t.get('instrument_token') == self.instrument_token:
                    self.trader.on_tick(t)
            self.trader.check_security()
        else:
            self.agg_10m.on_tick([tick])
            self.agg_30m.on_tick([tick])
            self.agg_1h.on_tick([tick])
            if tick.get('instrument_token') == self.instrument_token:
                self.trader.on_tick(tick)
            self.trader.check_security()

    def on_10m_closed(self, token, candle):
        if token != self.instrument_token: return
        if candle.index.tz: candle.index = candle.index.tz_localize(None)
        self.history_10m = pd.concat([self.history_10m, candle]).iloc[-self.config['lookbacks']['10m']:]
        self.run_strategy()

    def on_30m_closed(self, token, candle):
        if token != self.instrument_token: return
        if candle.index.tz: candle.index = candle.index.tz_localize(None)
        self.history_30m = pd.concat([self.history_30m, candle]).iloc[-self.config['lookbacks']['30m']:]

    def on_1h_closed(self, token, candle):
        if token != self.instrument_token: return
        if candle.index.tz: candle.index = candle.index.tz_localize(None)
        self.history_1h = pd.concat([self.history_1h, candle]).iloc[-self.config['lookbacks']['1h']:]

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
            existing = list(self.trader.portfolio.get_positions().keys())
            signals = self.strategy.generate_signals(data_map, datetime.now(), existing_positions=existing)
            if signals:
                logger.info(f"LIVE SIGNAL: {signals}")
                self.trader.process_signals(signals)
        except Exception as e:
            logger.error(f"LIVE Strategy Error: {e}", exc_info=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generic 3TF Live Runner')
    parser.add_argument('--symbol', type=str, required=True, help='Trading symbol')
    args = parser.parse_args()
    
    session = GenericLiveSession(args.symbol)
    session.run()
