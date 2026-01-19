"""
SBIN Paper Trading Runner
Monitors SBIN live and executes the Sentinel strategy in paper mode.
"""
import sys
import os
import pandas as pd
from datetime import datetime
import logging
import time

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.paper_trader import PaperTrader
from common.data_stream import DataStream
from common.aggregator import TickAggregator
from strategies.sbin.strategy import SbinSentinelStrategy

# Import from V2 for now (will be refactored)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from V2.Backtesting.data_fetcher import HistoricalDataFetcher
from V2.login import get_kite_instance

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SYMBOL = "SBIN"
INTERVAL_MIN = 5
LOOKBACK_WINDOW = 200

class SbinSentinelSession:
    """Live paper trading session for SBIN."""
    
    def __init__(self, initial_capital: float = 100000):
        self.kite = get_kite_instance()
        self.history: pd.DataFrame = None
        self.instrument_token = None
        self.current_date_str = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Initializing SBIN SENTINEL (V5)")
        
        # Components
        self.strategy = SbinSentinelStrategy(params={'bias': 'LONG'})
        self.trader = PaperTrader(initial_capital)
        self.aggregator = TickAggregator(interval_minutes=INTERVAL_MIN)
        
    def setup(self):
        """Fetch historical data and map instrument tokens."""
        logger.info(f"Fetching warmup data for {SYMBOL}...")
        fetcher = HistoricalDataFetcher(self.kite)
        end_date = datetime.now()
        start_date = end_date - pd.Timedelta(days=15)
        
        df = fetcher.fetch_historical_data(SYMBOL, start_date, end_date, interval=f"{INTERVAL_MIN}min")
        if not df.empty:
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            self.history = df.tail(LOOKBACK_WINDOW)
            logger.info(f"Loaded {len(df)} bars for {SYMBOL}")
        else:
            logger.error(f"Failed to fetch history for {SYMBOL}")
            sys.exit(1)
        
        # Get instrument token
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
        """Start the paper trading session."""
        self.setup()
        
        # Load access token
        with open("../V2/access_token.txt", "r") as f:
            access_token = f.read().strip()
        
        stream = DataStream(self.kite.api_key, access_token)
        stream.subscribe([self.instrument_token])
        stream.add_callback(self.on_tick)
        self.aggregator.add_callback(self.on_candle_closed)
        
        logger.info(f"🟢 SENTINEL ONLINE: Monitoring {SYMBOL}")
        stream.start()
        
        try:
            while True:
                time.sleep(30)
                status = self.trader.get_status()
                logger.info(f"💰 PnL: ₹{status['pnl']:.2f} | Positions: {status['positions']}")
        except KeyboardInterrupt:
            logger.info("Stopping Sentinel...")
            stream.stop()
    
    def on_tick(self, tick):
        """Handle incoming tick data."""
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
        """Handle candle close event."""
        if token != self.instrument_token:
            return
        
        if candle.index.tz is not None:
            candle.index = candle.index.tz_localize(None)
        
        # Update history
        if self.history is None:
            self.history = candle
        else:
            self.history = pd.concat([self.history, candle])
            self.history = self.history[~self.history.index.duplicated(keep='last')]
        
        # Trim to lookback window
        self.history = self.history.iloc[-LOOKBACK_WINDOW:]
        
        # Run strategy
        self.run_strategy()
    
    def run_strategy(self):
        """Execute strategy logic."""
        try:
            data_map = {SYMBOL: self.history}
            current_equity = self.trader.get_status()['total_value']
            existing_pos = list(self.trader.portfolio.get_positions().keys())
            
            signals = self.strategy.generate_signals(
                data_map,
                datetime.now(),
                capital=current_equity,
                existing_positions=existing_pos
            )
            
            if signals:
                logger.info(f"📊 SIGNAL: {signals[0].signal_type.value} @ {signals[0].price:.2f} | {signals[0].reason}")
                self.trader.process_signals(signals)
        except Exception as e:
            logger.error(f"Strategy error: {e}", exc_info=True)

if __name__ == "__main__":
    session = SbinSentinelSession(initial_capital=100000)
    session.run()
