import sys
import os
import pandas as pd
from datetime import datetime
import logging
import time
from typing import Dict, List, Tuple, Optional

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PaperTrader import PaperTrader
from DataStream_Engine import DataStream
from DataStream_Engine.aggregator import TickAggregator
from Algorithms import MultiFactorStrategy
from Database import DatabaseConnection, TradeRepository 
from Backtesting.config import BacktestConfig, StrategyConfig
from Backtesting.data_fetcher import HistoricalDataFetcher
from login import get_kite_instance

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Portfolio Configuration (Validated Basket)
BASKETS = {
    'Banking': ['SBIN', 'PNB', 'BANKBARODA', 'CANBK', 'IDFCFIRSTB']
}
SYMBOLS = [s for basket in BASKETS.values() for s in basket]
INTERVAL_MIN = 5
LOOKBACK_WINDOW = 300

class PaperRunningSession:
    def __init__(self):
        self.kite = get_kite_instance()
        self.history: Dict[str, pd.DataFrame] = {}
        self.token_map = {} 
        self.reverse_token_map = {}
        self.db = DatabaseConnection() 
        self.trade_repo = TradeRepository(self.db) 
        
        logger.info(f"Initializing V3 Multi-Factor Session for: {SYMBOLS}")
        
        # Init components with Tuned Parameters (Extreme Reversion)
        strategy_params = {
            'baskets': BASKETS,
            'z_threshold': 2.5,
            'lookback': LOOKBACK_WINDOW,
            'n_components': 1
        }
        self.strategy = MultiFactorStrategy(params=strategy_params)
        
        self.trader = PaperTrader(self.strategy, initial_capital=BacktestConfig.INITIAL_CAPITAL)
        self.aggregator = TickAggregator(interval_minutes=INTERVAL_MIN)
        
    def setup(self):
        # 1. Fetch initial history (Warmup)
        logger.info(f"Fetching warmup data ({LOOKBACK_WINDOW} bars)...")
        fetcher = HistoricalDataFetcher(self.kite)
        end_date = datetime.now()
        start_date = end_date - pd.Timedelta(days=30) 
        
        for symbol in SYMBOLS:
            df = fetcher.fetch_historical_data(symbol, start_date, end_date, interval=f"{INTERVAL_MIN}min")
            if not df.empty:
                if df.index.tz is not None:
                    df.index = df.index.tz_localize(None)
                self.history[symbol] = df.tail(LOOKBACK_WINDOW + 20)
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
                
        logger.info(f"Tokens mapped for {len(self.token_map)} symbols")
        
    def run(self):
        self.setup()
        
        # Use existing access token
        with open("access_token.txt", "r") as f:
            access_token = f.read().strip()
            
        stream = DataStream(self.kite.api_key, access_token) 
        
        # Subscribe
        tokens = list(self.token_map.keys())
        stream.subscribe(tokens)
        
        # Connect Callbacks
        stream.add_callback(self.on_tick)
        self.aggregator.add_callback(self.on_candle_closed)
        
        logger.info(f"Starting Paper Trading V3 for Banking Basket")
        stream.start()
        
        try:
            while True:
                time.sleep(30)
                status = self.trader.get_status()
                logger.info(f"PnL: {status['total_value'] - BacktestConfig.INITIAL_CAPITAL:.2f} | Open Pos: {len(status['portfolio']['positions'])}")
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
            token = tick.get('instrument_token')
            if token in self.token_map:
                self.trader.current_prices[self.token_map[token]] = tick.get('last_price')

    def on_candle_closed(self, token_or_symbol, candle):
        symbol = self.token_map.get(token_or_symbol)
        if not symbol: return
            
        if candle.index.tz is not None:
            candle.index = candle.index.tz_localize(None)
            
        logger.info(f"New Candle {symbol}: {candle.iloc[-1]['close']}")
        
        # Update History
        if symbol not in self.history:
            self.history[symbol] = candle
        else:
            self.history[symbol] = pd.concat([self.history[symbol], candle])
        
        # Trim
        if len(self.history[symbol]) > LOOKBACK_WINDOW * 2:
             self.history[symbol] = self.history[symbol].iloc[-LOOKBACK_WINDOW-20:]
             
        self.run_strategy()

    def run_strategy(self):
        try:
            # Ensure we have data for all symbols
            if len(self.history) < len(SYMBOLS): return
            
            data_map = {s: self.history[s] for s in SYMBOLS}
            current_equity = self.trader.get_status()['total_value']
            
            signals = self.strategy.generate_signals(data_map, datetime.now(), capital=current_equity)
            
            if signals:
                logger.info(f"Generated {len(signals)} signals: {signals}")
                self.trader.process_signals(signals)
                
        except Exception as e:
            logger.error(f"Strategy Error: {e}")

if __name__ == "__main__":
    session = PaperRunningSession()
    session.run()
