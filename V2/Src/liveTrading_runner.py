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
from Common.quant_utils import round_to_tick
from Src.login import get_kite_instance
from config_3tf import CONFIG

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GenericLiveSession:
    def __init__(self, symbol: str):
        self.symbol = symbol.upper()
        if self.symbol not in CONFIG:
            if "DEFAULT" in CONFIG:
                logger.warning(f"Symbol {self.symbol} not found in config. Using DEFAULT settings.")
                self.config = CONFIG["DEFAULT"]
            else:
                raise ValueError(f"Symbol {self.symbol} not found in config_3tf.py and no DEFAULT set.")
        else:
            self.config = CONFIG[self.symbol]
        self.kite = get_kite_instance()
        self.history_tree: pd.DataFrame = None
        self.history_30m: pd.DataFrame = None
        self.history_1h: pd.DataFrame = None
        self.instrument_token = None
        
        # INDEX TRACKING (V8.1)
        self.index_tokens = {
            'NIFTY': 256,
            'BANKNIFTY': 260
        }
        self.index_mapping = {
            'NIFTY': 'NIFTY 50',
            'BANKNIFTY': 'NIFTY BANK'
        }
        self.index_data = {
            'NIFTY': {'10m': None, 'agg': TickAggregator(interval_minutes=10), 'bias': 'NEUTRAL'},
            'BANKNIFTY': {'10m': None, 'agg': TickAggregator(interval_minutes=10), 'bias': 'NEUTRAL'}
        }
        
        logger.info(f"Initializing LIVE 3-TIMEFRAME MTFA SESSION for {self.symbol}")
        
        # Init Strategy
        params = self.config['strategy_params'].copy()
        params['symbol'] = self.symbol
        self.strategy = Generic3TFStrategy(params=params)
        
        # Init LIVE Trader
        self.trader = LiveTrader(self.kite, self.strategy)
        self.tick_size = params.get('tick_size', 0.05)
        
        # Triple Aggregators (Adaptive Tree Timeframe)
        self.tree_interval = params.get('tree_interval', 10)
        self.agg_tree = TickAggregator(interval_minutes=self.tree_interval)
        self.agg_30m = TickAggregator(interval_minutes=30)
        self.agg_1h = TickAggregator(interval_minutes=60)
        
        self.volume_profile = {'vah': None, 'val': None, 'poc': None}
        
    def setup(self):
        logger.info(f"Fetching LIVE MTFA warmup data for {self.symbol}...")
        fetcher = HistoricalDataFetcher(self.kite)
        end_date = datetime.now()
        lookbacks = self.config['lookbacks']
        
        # 1. Warmup
        tree_interval_str = f"{self.tree_interval}minute"
        self.history_tree = fetcher.fetch_historical_data(self.symbol, end_date - timedelta(days=5), end_date, interval=tree_interval_str).tail(self.config['lookbacks']['10m'])
        self.history_30m = fetcher.fetch_historical_data(self.symbol, end_date - timedelta(days=10), end_date, interval="30minute").tail(lookbacks['30m'])
        self.history_1h = fetcher.fetch_historical_data(self.symbol, end_date - timedelta(days=20), end_date, interval="60minute").tail(lookbacks['1h'])
        
        # Warmup Indices (Only if needed by the symbol)
        corr_index = self.config['strategy_params'].get('correlated_index', 'NONE')
        if corr_index != 'NONE':
            for idx_name, idx_token in self.index_tokens.items():
                if idx_name != corr_index: continue
                
                fetch_name = self.index_mapping.get(idx_name, idx_name)
                logger.info(f"Warmup Index: {fetch_name}")
                idx_df = fetcher.fetch_historical_data(fetch_name, end_date - timedelta(days=5), end_date, interval="10minute").tail(50)
                if idx_df is not None and not idx_df.empty:
                    if idx_df.index.tz: idx_df.index = idx_df.index.tz_localize(None)
                    self.index_data[idx_name]['10m'] = idx_df
                    self._calculate_index_bias(idx_name)
        else:
            logger.info(f"Skipping Index Warmup for {self.symbol} (Correlated Index: NONE)")
 
        # 1.1 Volume Profile Setup (Phase 4)
        self._setup_volume_profile(fetcher)
 
        for df in [self.history_tree, self.history_30m, self.history_1h]:
            if df is not None and not df.empty and df.index.tz:
                df.index = df.index.tz_localize(None)
                
        # 2. Token Mapping
        instruments = self.kite.instruments("NSE")
        for inst in instruments:
            if inst['tradingsymbol'] == self.symbol:
                self.instrument_token = inst['instrument_token']
                self.tick_size = inst.get('tick_size', 0.05)
                break
        
        if not self.instrument_token:
            logger.error(f"Token not found for {self.symbol}")
            sys.exit(1)
            
        # 3. Inject Actual Tick Size into Strategy and Local state
        self.strategy.tick_size = self.tick_size
        logger.info(f"Token: {self.instrument_token} | Actual Tick Size: {self.tick_size}")
 
    def _calculate_index_bias(self, name: str):
        df = self.index_data[name]['10m']
        if df is None or len(df) < 20: return
        ema = df['close'].ewm(span=20, adjust=False).mean()
        last_price = df['close'].iloc[-1]
        last_ema = ema.iloc[-1]
        self.index_data[name]['bias'] = "BULLISH" if last_price > last_ema else "BEARISH"
        logger.info(f"INDEX STATE | {name} | Price: {last_price:.2f} | EMA20: {last_ema:.2f} | Bias: {self.index_data[name]['bias']}")
 
    def _setup_volume_profile(self, fetcher):
        """Fetches yesterday's 1m data and calculates VAH/VAL/POC"""
        from Common.quant_utils import calculate_volume_profile
        logger.info(f"Calculating Volume Profile for {self.symbol}...")
        
        # We need historical data for the LAST trading day
        # Fetching last 3 days to ensure we get a full day of data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=3)
        
        df_1m = fetcher.fetch_historical_data(self.symbol, start_date, end_date, interval="minute")
        if df_1m.empty:
            logger.warning("No 1m data found for Volume Profile. Skipping.")
            return
 
        # Get data for the last COMPLETE trading day (before today)
        today = datetime.now().date()
        df_1m.index = pd.to_datetime(df_1m.index)
        yesterday_data = df_1m[df_1m.index.date < today]
        
        if yesterday_data.empty:
            logger.warning("No historical 1m data (prior to today) found for Volume Profile.")
            return
            
        last_trading_day = yesterday_data.index.date[-1]
        last_day_df = yesterday_data[yesterday_data.index.date == last_trading_day]
        
        self.volume_profile = calculate_volume_profile(last_day_df)
        self.strategy.volume_profile = self.volume_profile
        logger.info(f"VOLUME PROFILE | Day: {last_trading_day} | VAH: {self.volume_profile['vah']} | VAL: {self.volume_profile['val']} | POC: {self.volume_profile['poc']}")
 
    def run(self):
        self.setup()
        
        with open("access_token.txt", "r") as f:
            access_token = f.read().strip()
            
        stream = DataStream(self.kite.api_key, access_token)
        # Subscribe to Symbol AND Indices
        tokens_to_subscribe = [self.instrument_token] + list(self.index_tokens.values())
        stream.subscribe(tokens_to_subscribe)
        stream.add_callback(self.on_tick)
        
        self.agg_tree.add_callback(self.on_tree_closed)
        self.agg_30m.add_callback(self.on_30m_closed)
        self.agg_1h.add_callback(self.on_1h_closed)
        
        # Index Callbacks
        for name, token in self.index_tokens.items():
            self.index_data[name]['agg'].add_callback(
                lambda t, c, n=name, tok=token: self.on_index_tree_closed(n, c) if t == tok else None
            )
        
        logger.info(f"LIVE 3TF MTFA ONLINE: Monitoring {self.symbol} (Index Filtering Enabled)")
        stream.start()
        
        try:
            while True:
                time.sleep(5)
                self.trader.sync_and_cleanup()
                
                # Slower logging (every 30s approx)
                if int(time.time()) % 30 < 5:
                    status = self.trader.get_status()
                    logger.info(f"LIVE {self.symbol} Monitoring | Positions: {status['positions']}")
        except KeyboardInterrupt:
            logger.info("Stopping Session...")
            self.trader.shutdown()
            stream.stop()
 
    def on_tick(self, tick, symbol_override: str = None):
        ticks = tick if isinstance(tick, list) else [tick]
        
        self.agg_tree.on_tick(ticks)
        self.agg_30m.on_tick(ticks)
        self.agg_1h.on_tick(ticks)
        
        # Dispatch to Index Aggregators
        for name, token in self.index_tokens.items():
            self.index_data[name]['agg'].on_tick(ticks)
 
        for t in ticks:
            if t.get('instrument_token') == self.instrument_token:
                self.latest_tick = t
                self.trader.on_tick(t, symbol_override=self.symbol)
        
        self.trader.check_security()
 
    def on_index_tree_closed(self, name, candle):
        if candle.index.tz: candle.index = candle.index.tz_localize(None)
        self.index_data[name]['10m'] = pd.concat([self.index_data[name]['10m'], candle]).tail(50)
        self._calculate_index_bias(name)
 
    def on_tree_closed(self, token, candle):
        if token != self.instrument_token: return
        if candle.index.tz: candle.index = candle.index.tz_localize(None)
        self.history_tree = pd.concat([self.history_tree, candle]).iloc[-self.config['lookbacks']['10m']:]
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
        if self.history_tree is None or self.history_30m is None or self.history_1h is None: return
        try:
            data_map = {
                self.symbol: {
                    'tree': self.history_tree,
                    '30minute': self.history_30m,
                    '1hour': self.history_1h
                }
            }
            positions = self.trader.portfolio.get_positions()
            existing = list(positions.keys())
            
            # --- ADVANCED SYNC (V7.0): Adopt existing positions & Analyze Orders ---
            if self.symbol in existing and self.symbol not in self.trader.security_targets:
                pos = positions[self.symbol]
                side = 'LONG' if pos.quantity > 0 else 'SHORT'
                logger.info(f"SYNC: Found existing {self.symbol} {side} (Qty: {pos.quantity}). Analysing protection...")
                
                # 1. Fetch current Broker State
                broker_orders = self.kite.orders()
                open_orders = [o for o in broker_orders if o['tradingsymbol'] == self.symbol and o['status'] in ('OPEN', 'TRIGGER PENDING')]
                
                # 2. Calculate what the protection *should* be
                sl_pct = self.strategy.stop_loss_pct
                tp_pct = self.strategy.profit_target_pct
                curr_price = self.history_tree['close'].iloc[-1]
                
                # Calculate ideal prices (based on entry if available, otherwise curr_price)
                ref_price = pos.entry_price if pos.entry_price > 0 else curr_price
                sl_ideal = round_to_tick(ref_price * (1 - sl_pct), self.tick_size) if side == 'LONG' else round_to_tick(ref_price * (1 + sl_pct), self.tick_size)
                tp_ideal = round_to_tick(ref_price * (1 + tp_pct), self.tick_size) if side == 'LONG' else round_to_tick(ref_price * (1 - tp_pct), self.tick_size)
                be_ideal = round_to_tick(ref_price * (1 + tp_pct * 0.7), self.tick_size) if side == 'LONG' else round_to_tick(ref_price * (1 - tp_pct * 0.7), self.tick_size)
                
                # 3. Analyze and Adopt Target Order
                found_tp = next((o for o in open_orders if o['order_type'] == 'LIMIT' and abs(o['price'] - tp_ideal) < 0.2), None)
                if found_tp:
                    self.trader.active_limit_orders[self.symbol] = found_tp['order_id']
                    logger.info(f"SYNC: Adopted existing TARGET LIMIT order {found_tp['order_id']} @ {found_tp['price']}")
                else:
                    logger.warning(f"SYNC: No matching Target order found. Placing new Limit @ {tp_ideal}")
                    try:
                        if side == 'LONG': limit_id = self.trader.sell_limit.execute(self.symbol, abs(pos.quantity), tp_ideal)
                        else: limit_id = self.trader.buy_limit.execute(self.symbol, abs(pos.quantity), tp_ideal)
                        self.trader.active_limit_orders[self.symbol] = limit_id
                    except Exception as e: logger.error(f"SYNC TP placement failed: {e}")
 
                # 4. Analyze and Adopt SL Order
                found_sl = next((o for o in open_orders if o['order_type'] == 'SL-M' and abs(o['trigger_price'] - sl_ideal) < 0.2), None)
                if found_sl:
                    self.trader.active_sl_orders[self.symbol] = found_sl['order_id']
                    logger.info(f"SYNC: Adopted existing STOP-LOSS order {found_sl['order_id']} @ {found_sl['trigger_price']}")
                else:
                    logger.warning(f"SYNC: No matching SL order found on Broker. Placing new SL-M @ {sl_ideal}")
                    try:
                        if side == 'LONG': sl_id = self.trader.sell_slm.execute(self.symbol, abs(pos.quantity), sl_ideal)
                        else: sl_id = self.trader.buy_slm.execute(self.symbol, abs(pos.quantity), sl_ideal)
                        self.trader.active_sl_orders[self.symbol] = sl_id
                    except Exception as e: logger.error(f"SYNC SL placement failed: {e}")
 
                # 5. Initialize Security Tracking locally
                self.trader.security_targets[self.symbol] = {
                    'sl': found_sl['trigger_price'] if found_sl else sl_ideal,
                    'tp': found_tp['price'] if found_tp else tp_ideal,
                    'be_trig': be_ideal, 'be_moved': False, 'peak': curr_price
                }
                self.strategy.trade_info[self.symbol] = {'entry_price': ref_price, 'side': side, 'sl_price': self.trader.security_targets[self.symbol]['sl']}
            # -------------------------------------------------------
 
            # Index Bias Dictionary
            indices_bias = {name: data['bias'] for name, data in self.index_data.items()}
            
            # FETCH ACTUAL CAPITAL 
            margins = self.trader.portfolio.get_margins()
            available = margins.get('equity', {}).get('available', {}).get('cash', 50000)
            
            signals = self.strategy.generate_signals(
                data_map, 
                datetime.now(), 
                capital=available, 
                existing_positions=existing,
                tick_data={self.symbol: self.latest_tick} if hasattr(self, 'latest_tick') else None,
                indices_bias=indices_bias,
                volume_profile=self.volume_profile
            )
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
