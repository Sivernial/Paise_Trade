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
        self.tick_size = params.get('tick_size', 0.05)
        
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
                self.tick_size = inst.get('tick_size', 0.05)
                break
        
        if not self.instrument_token:
            logger.error(f"Token not found for {self.symbol}")
            sys.exit(1)
            
        # 3. Inject Actual Tick Size into Strategy and Local state
        self.strategy.tick_size = self.tick_size
        logger.info(f"Token: {self.instrument_token} | Actual Tick Size: {self.tick_size}")

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
                time.sleep(5) # Faster heart-beat for janitor
                self.trader.sync_and_cleanup()
                
                # Slower logging (every 30s approx)
                if int(time.time()) % 30 < 5:
                    status = self.trader.get_status()
                    logger.info(f"LIVE {self.symbol} Monitoring | Positions: {status['positions']}")
        except KeyboardInterrupt:
            logger.info("Stopping Session...")
            self.trader.shutdown()
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
                curr_price = self.history_10m['close'].iloc[-1]
                
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
