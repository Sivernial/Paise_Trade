import sys
import os
import pandas as pd
from datetime import datetime
import logging
import time

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PaperTrader import PaperTrader
from DataStream_Engine import DataStream
from DataStream_Engine.aggregator import TickAggregator
from Algorithms import PairTradingStrategy
from Database import DatabaseConnection, TradeRepository
from Backtesting.config import BacktestConfig, StrategyConfig
from Backtesting.data_fetcher import HistoricalDataFetcher
from login import get_kite_instance

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- INTRADAY CONFIGURATION ---
CONFIG = StrategyConfig.INTRADAY_PAIR_TRADING
PAIR = CONFIG['pairs'][0] # Default to first pair
SYMBOLS = list(PAIR)
INTERVAL_MIN = 5 # 5 Minute Candles
LOOKBACK_WINDOW = CONFIG['lookback_window']

class IntradayRunningSession:
    def __init__(self):
        self.kite = get_kite_instance()
        self.history = {}
        self.token_map = {} 
        self.reverse_token_map = {}
        self.db = DatabaseConnection()
        self.trade_repo = TradeRepository(self.db)
        
        # --- DYNAMIC PAIR SCANNING ---
        # For intraday, we might want to stick to config pairs or scan pre-market.
        # Here we use config pairs for stability.
        self.pairs = CONFIG['pairs']
        logger.info(f"⚡️ Intraday Pairs: {self.pairs}")

        # Update Global SYMBOLS
        global SYMBOLS
        unique_syms = set()
        for p in self.pairs:
            unique_syms.add(p[0])
            unique_syms.add(p[1])
        SYMBOLS = list(unique_syms)
        logger.info(f"Active Symbols: {SYMBOLS}")

        # Init Strategy with INTRADAY Config
        strategy_params = CONFIG.copy()
        self.strategy = PairTradingStrategy(params=strategy_params)
        
        # Init KF Registry
        self.strategy.kf_registry = {}
        from Common.quant_utils import KalmanFilterReg
        for pair in self.pairs:
            self.strategy.kf_registry[pair] = KalmanFilterReg(delta=1e-4, R=1e-3)
            
        self.trader = PaperTrader(self.strategy, initial_capital=BacktestConfig.INITIAL_CAPITAL)
        self.aggregator = TickAggregator(interval_minutes=INTERVAL_MIN)
        
    def setup(self):
        # 1. Fetch initial history (Warmup)
        logger.info(f"Fetching warmup data ({LOOKBACK_WINDOW} bars)...")
        fetcher = HistoricalDataFetcher(self.kite)
        end_date = datetime.now()
        # Fetch enough history for 5min bars
        # 60 bars * 5 min = 300 min = 5 hours. Fetch 2 days to be safe.
        start_date = end_date - pd.Timedelta(days=5) 
        
        for symbol in SYMBOLS:
            df = fetcher.fetch_historical_data(symbol, start_date, end_date, interval=f"{INTERVAL_MIN}min")
            if not df.empty:
                # Force tz-naive
                if df.index.tz is not None:
                    df.index = df.index.tz_localize(None)
                self.history[symbol] = df.tail(LOOKBACK_WINDOW + 10)
                logger.info(f"Loaded {len(self.history[symbol])} bars for {symbol}")
            else:
                logger.error(f"Failed to fetch history for {symbol}")
                # For paper trading, we might survive partial failure, but better to exit
                sys.exit(1)
                
        # 2. Get Instrument Tokens
        instruments = self.kite.instruments("NSE")
        for inst in instruments:
            if inst['tradingsymbol'] in SYMBOLS:
                self.token_map[inst['instrument_token']] = inst['tradingsymbol']
                self.reverse_token_map[inst['tradingsymbol']] = inst['instrument_token']
                
        logger.info(f"Tokens: {self.token_map}")
        
    def run(self):
        self.setup()
        
        # Setup Stream
        try:
            with open("access_token.txt", "r") as f:
                access_token = f.read().strip()
        except:
             logger.error("Access Token missing. Login first.")
             return
            
        stream = DataStream(self.kite.api_key, access_token)
        
        tokens = list(self.token_map.keys())
        stream.subscribe(tokens)
        
        stream.add_callback(self.on_tick)
        self.aggregator.add_callback(self.on_candle_closed)
        
        logger.info(f"Starting INTRADAY Trading Session. Exit Time: {CONFIG.get('time_stop')}")
        stream.start()
        
        try:
            while True:
                time.sleep(10)
                status = self.trader.get_status()
                logger.info(f"Portfolio: Rs {status['total_value']:.2f} | Open Pos: {status['portfolio']['positions']}")
                
                # Check for Market Close (3:30 PM) to stop script
                now = datetime.now()
                if now.hour == 15 and now.minute >= 30:
                    logger.info("Market Closed. Stopping Session.")
                    break
                    
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
             self.history[symbol] = self.history[symbol].iloc[-LOOKBACK_WINDOW:]
             
        self.run_strategy()

    def run_strategy(self):
        try:
            data_map = {s: self.history[s] for s in SYMBOLS if s in self.history}
            current_equity = self.trader.get_status()['total_value']
            
            # Pass current_date explicitly for time checks
            signals = self.strategy.generate_signals(data_map, datetime.now(), capital=current_equity)
            
            # Log State
            if hasattr(self.strategy, 'latest_state'):
                for pair_key, state in self.strategy.latest_state.items():
                    pair_str = f"{pair_key[0]}-{pair_key[1]}"
                    logger.info(f"State {pair_str}: Z={state['z_score']:.2f} Loop={state.get('loop_time','')}")
                    self.trade_repo.log_strategy_state(
                        pair_str,
                        state['z_score'],
                        state['beta'],
                        state['spread'],
                        0.0,
                        'SIGNAL' if signals else 'NONE'
                    )
            
            if signals:
                logger.info(f"Signals generated: {signals}")
                self.trader.process_signals(signals)
                
        except Exception as e:
            logger.error(f"Strategy Error: {e}")

if __name__ == "__main__":
    session = IntradayRunningSession()
    session.run()
