import sys
import os
import pandas as pd
from datetime import datetime
import logging
import time
from typing import Dict, List, Tuple, Optional

# Add parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from LiveTrader import LiveTrader
from DataStream_Engine import DataStream
from DataStream_Engine.aggregator import TickAggregator
from Algorithms import MultiFactorStrategy
from Backtesting.config import BacktestConfig, StrategyConfig
from Backtesting.data_fetcher import HistoricalDataFetcher
from Database.connection import DatabaseConnection
from Database.trade_repository import TradeRepository
from Common.notifier import notifier
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
        self.db = DatabaseConnection()
        self.trade_repo = TradeRepository(self.db)
        
        # Init Strategy with Extreme Tuning (Z=2.5)
        strategy_params = {
            'baskets': BASKETS,
            'z_threshold': 2.5,
            'lookback': LOOKBACK_WINDOW,
            'n_components': 1
        }
        self.strategy = MultiFactorStrategy(params=strategy_params)
        
        self.trader = LiveTrader(self.kite, self.strategy) 
        self.aggregator = TickAggregator(interval_minutes=INTERVAL_MIN)
        
    def setup(self):
        # 1. Fetch Warmup
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
                
        # 2. Map Tokens
        instruments = self.kite.instruments("NSE")
        for inst in instruments:
            if inst['tradingsymbol'] in SYMBOLS:
                self.token_map[inst['instrument_token']] = inst['tradingsymbol']
                
        logger.info(f"Tokens mapped for {len(self.token_map)} symbols")
        
    def run(self):
        self.setup()
        
        with open("access_token.txt", "r") as f:
            access_token = f.read().strip()
            
        stream = DataStream(self.kite.api_key, access_token)
        stream.subscribe(list(self.token_map.keys()))
        
        stream.add_callback(self.on_tick)
        self.aggregator.add_callback(self.on_candle_closed)
        
        logger.info(f"Starting LIVE Trading V3 for Banking Basket")
        stream.start()
        
        try:
            while True:
                time.sleep(30)
                # Keep session alive and log heartbeat
                # status = self.trader.get_status() # Optional: Log balance periodically
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
        
        if candle.index.tz is not None:
             candle.index = candle.index.tz_localize(None)

        logger.info(f"New Candle {symbol}: {candle.iloc[-1]['close']}")
        
        if symbol not in self.history:
            self.history[symbol] = candle
        else:
             self.history[symbol] = pd.concat([self.history[symbol], candle])
        
        if len(self.history[symbol]) > LOOKBACK_WINDOW * 2:
             self.history[symbol] = self.history[symbol].iloc[-LOOKBACK_WINDOW-20:]
             
        self.run_strategy()

    def run_strategy(self):
        try:
            if len(self.history) < len(SYMBOLS): return
            
            data_map = {s: self.history[s] for s in SYMBOLS}
            
            # Fetch Live Balance for Risk Sizing
            margins = self.kite.margins()
            current_equity = margins.get('equity', {}).get('available', {}).get('live_balance', 100000)
            
            signals = self.strategy.generate_signals(data_map, datetime.now(), capital=current_equity)
            
            if signals:
                logger.info(f"LIVE SIGNALS: {signals}")
                # notifier.send(f"⚠️ LIVE TRADING SIGNAL: {signals}")
                self.trader.process_signals(signals)
                
        except Exception as e:
            logger.error(f"Live Strategy Error: {e}")
            notifier.send(f"🛑 LIVE ERROR: {e}")

if __name__ == "__main__":
    session = LiveRunningSession()
    session.run()
