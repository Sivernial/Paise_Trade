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
from Algorithms import MultiFactorStrategy
from Database import DatabaseConnection, TradeRepository 
from reporting_engine import ReportingEngine
from Backtesting.config import BacktestConfig, StrategyConfig
from Backtesting.data_fetcher import HistoricalDataFetcher
from login import get_kite_instance

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Portfolio Configuration (Multi-Sector Recovery)
BASKETS = {
    'Banking': ['SBIN', 'PNB', 'BANKBARODA', 'CANBK', 'IDFCFIRSTB'],
    'IT': ['INFY', 'TCS', 'HCLTECH', 'TECHM', 'WIPRO'],
    'Auto': ['MARUTI', 'M&M', 'TMPV', 'BAJAJ-AUTO', 'EICHERMOT'],
    'Pharma': ['SUNPHARMA', 'CIPLA', 'DRREDDY', 'DIVISLAB'],
    'Energy': ['RELIANCE', 'NTPC', 'POWERGRID', 'ONGC', 'COALINDIA']
}
SYMBOLS = [s for basket in BASKETS.values() for s in basket]
INTERVAL_MIN = 5
LOOKBACK_WINDOW = 180 # Faster adaptation

class PaperRunningSession:
    def __init__(self):
        self.kite = get_kite_instance()
        self.history: Dict[str, pd.DataFrame] = {}
        self.token_map = {} 
        self.reverse_token_map = {}
        self.db = DatabaseConnection() 
        self.trade_repo = TradeRepository(self.db) 
        self.reporter = ReportingEngine()
        self.current_date_str = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Initializing V3 Multi-Factor Session for: {SYMBOLS}")
        
        # Init components with Tiered Parameters
        strategy_params = {
            'baskets': BASKETS,
            'z_threshold': 2.0, 
            'exit_z_threshold': 1.0, # Greedier Exit
            'tiered_thresholds': {
                'Banking': 2.0,
                'IT': 2.5,
                'Auto': 2.5,
                'Pharma': 2.5,
                'Energy': 2.5
            },
            'lookback': LOOKBACK_WINDOW,
            'n_components': 1
        }
        # Try to load optimized thresholds from a previous cycle
        optimized_config = self._load_strategy_config()
        if optimized_config:
            strategy_params['symbol_thresholds'] = optimized_config.get('symbol_thresholds', {})
            logger.info("Loaded AUTOMATED Z-TUNING configuration.")
        
        self.strategy = MultiFactorStrategy(params=strategy_params)
        
        self.trader = PaperTrader(self.strategy, initial_capital=BacktestConfig.INITIAL_CAPITAL, trade_repo=self.trade_repo)
        self.aggregator = TickAggregator(interval_minutes=INTERVAL_MIN)
        
    def _load_strategy_config(self):
        """Load optimized thresholds from disk if they exist."""
        path = "strategy_config.json"
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load strategy_config.json: {e}")
        return None
        
    def _reload_config(self):
        """Reload the strategy configuration dynamically."""
        new_config = self._load_strategy_config()
        if new_config:
            # Update the strategy's internal params dict in-place
            self.strategy.params['symbol_thresholds'] = new_config.get('symbol_thresholds', {})
            logger.info("Auto-Tuning: Configuration reloaded with new Z-thresholds.")

    def setup(self):
        # 1. Fetch initial history (Warmup)
        logger.info(f"Fetching warmup data for {len(SYMBOLS)} symbols...")
        fetcher = HistoricalDataFetcher(self.kite)
        end_date = datetime.now()
        start_date = end_date - pd.Timedelta(days=40) # 40 days to ensure 300 bars per asset
        
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
                
        # 2. Database Maintenance (Rolling 4-month window)
        self.db.prune_old_data(days=120)
                
        # 3. Get Instrument Tokens
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
                # Check for day change to generate report
                now_str = datetime.now().strftime('%Y-%m-%d')
                if now_str != self.current_date_str:
                    logger.info(f"Day change detected. Generating report for {self.current_date_str}")
                    self.reporter.generate_daily_report(self.current_date_str)
                    self._reload_config() # Reload optimized params for the new day
                    self.current_date_str = now_str

                status = self.trader.get_status()
                logger.info(f"PnL: {status['total_value'] - BacktestConfig.INITIAL_CAPITAL:.2f} | Open Pos: {len(status['portfolio']['positions'])}")
        except KeyboardInterrupt:
            logger.info("Stopping... Generating final report.")
            self.reporter.generate_daily_report(self.current_date_str)
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
            
        logger.debug(f"New Candle {symbol}: {candle.iloc[-1]['close']}")
        
        # Update History
        if symbol not in self.history:
            self.history[symbol] = candle
        else:
            self.history[symbol] = pd.concat([self.history[symbol], candle])
            # De-duplicate: Keep the most recent data for overlapping timestamps
            self.history[symbol] = self.history[symbol][~self.history[symbol].index.duplicated(keep='last')]
        
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
            
            # Identify existing positions for the strategy
            existing_pos = list(self.trader.portfolio.get_positions().keys())
            
            signals = self.strategy.generate_signals(
                data_map, 
                datetime.now(), 
                capital=current_equity,
                existing_positions=existing_pos
            )
            
            if signals:
                logger.info(f"Generated {len(signals)} signals: {signals}")
                self.trader.process_signals(signals)
            
            # --- PERFORMANCE HARVESTING ---
            metrics = self.strategy.last_metrics
            if metrics:
                self.trade_repo.log_performance_metrics(metrics)
                # logger.debug(f"Logged performance metrics for {len(metrics)} symbols")
                
        except Exception as e:
            logger.error(f"Strategy Error: {e}")

if __name__ == "__main__":
    session = PaperRunningSession()
    session.run()
