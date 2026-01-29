from typing import Dict, List
from datetime import datetime
from kiteconnect import KiteConnect
from .portfolio import LivePortfolio
from Algorithms.base_strategy import BaseStrategy
from Common import Signal, SignalType
from DataStream_Engine import BuyInstant, SellInstant, BuyLimit, SellLimit, BuySLM, SellSLM
import logging
import time

logger = logging.getLogger(__name__)

class LiveTrader:
    
    def __init__(self, kite: KiteConnect, strategy: BaseStrategy):
        self.kite = kite
        self.strategy = strategy
        self.portfolio = LivePortfolio(kite)
        self.buy_action = BuyInstant(kite)
        self.sell_action = SellInstant(kite)
        self.buy_limit = BuyLimit(kite)
        self.sell_limit = SellLimit(kite)
        self.buy_slm = BuySLM(kite)
        self.sell_slm = SellSLM(kite)
        self.current_prices: Dict[str, float] = {}
        self.security_targets: Dict[str, Dict[str, float]] = {} # Tracks SL/TP/BE/Trail
        self.active_limit_orders: Dict[str, str] = {} # symbol -> order_id
        self.active_sl_orders: Dict[str, str] = {} # symbol -> order_id
        self.max_capital = self.strategy.params.get('max_capital')
    
    def on_tick(self, tick):
        symbol = tick.get('tradingsymbol')
        price = tick.get('last_price', 0)
        
        if symbol and price:
            self.current_prices[symbol] = price
    
    def process_signals(self, signals: List[Signal]):
        for signal in signals:
            if signal.signal_type == SignalType.BUY:
                self._execute_buy(signal)
            elif signal.signal_type == SignalType.SELL:
                self._execute_sell(signal)
            elif signal.signal_type == SignalType.EXIT:
                self._execute_exit(signal)

    def check_security(self):
        """
        Polls current prices against SL/TP/BE/Trail targets on every tick.
        """
        if not self.security_targets: return
        
        positions = self.portfolio.get_positions()
        
        for symbol, targets in list(self.security_targets.items()):
            # 1. POSITION SYNC: If position is gone (Broker-side exit), nuke ALL stray orders
            if symbol not in positions:
                logger.info(f"SECURITY: Position for {symbol} no longer found on Broker. Cleaning up ALL pending orders...")
                self._cancel_all_open_orders(symbol)
                self._cleanup_tracking(symbol)
                continue
            
            # 2. PRICE SYNC: Only proceed to SL/TP check if we have a fresh price
            price = self.current_prices.get(symbol)
            if not price: continue
                
            pos = positions[symbol]
            is_long = pos.quantity > 0
            entry_price = pos.entry_price
            
            sl = targets.get('sl')
            be_trig = targets.get('be_trig')
            trail_trig = targets.get('trail_trig')
            
            # 1. Breakeven logic (Move SL to entry)
            if be_trig and not targets.get('be_moved'):
                hit_be = (is_long and price >= be_trig) or (not is_long and price <= be_trig)
                if hit_be:
                    targets['sl'] = entry_price
                    targets['be_moved'] = True
                    logger.info(f"SAFETY NET: Moving Stop Loss to BREAKEVEN ({entry_price:.2f}) for {symbol}")

            # 2. Trailing Stop logic (Emergency Market Exit if 90% reached and reversing)
            if trail_trig:
                # If we've hit 90% target, and price drops 0.3% from peak (or since trig)
                peak = targets.get('peak', price)
                if is_long:
                    targets['peak'] = max(peak, price)
                    emergency_exit = (price >= trail_trig) and (price < targets['peak'] * 0.997)
                else:
                    targets['peak'] = min(peak, price)
                    emergency_exit = (price <= trail_trig) and (price > targets['peak'] * 1.003)

                if emergency_exit:
                    reason = f"SAFETY NET EXIT: Trail Hit for {symbol} @ {price:.2f} (Locking profits)"
                    logger.warning(reason)
                    self._execute_exit(Signal(symbol, SignalType.EXIT, price, datetime.now(), 0, reason))
                    continue

            # 3. Check Stop Loss
            hit_sl = False
            if sl:
                if is_long and price <= sl: hit_sl = True
                elif not is_long and price >= sl: hit_sl = True
                
            if hit_sl:
                reason = f"LIVE SECURITY EXIT: Stop Loss hit at {price:.2f} (Target: {sl:.2f})"
                logger.warning(reason)
                self._execute_exit(Signal(symbol, SignalType.EXIT, price, datetime.now(), 0, reason))
                continue

    def _execute_buy(self, signal: Signal):
        """Execute buy order and immediately place target limit order."""
        positions = self.portfolio.get_positions()
        pos = positions.get(signal.symbol)
        
        is_cover = pos and pos.quantity < 0
        quantity = abs(pos.quantity) if is_cover else (signal.quantity or self._calculate_quantity(signal.symbol, signal.price))
        
        try:
            order_id = self.buy_action.execute(signal.symbol, quantity)
            logger.info(f"Live BUY MARKET order placed: {order_id} for {quantity} {signal.symbol}")
            
            if not is_cover:
                # 1. Store Security Targets
                self.security_targets[signal.symbol] = {
                    'sl': signal.stop_loss,
                    'tp': signal.target,
                    'be_trig': signal.breakeven_trigger,
                    'trail_trig': signal.partial_exit_trigger,
                    'be_moved': False,
                    'peak': signal.price
                }
                # 2. Place Limit Order for Target
                if signal.target:
                    time.sleep(0.5) # Small buffer for position to sync
                    limit_id = self.sell_limit.execute(signal.symbol, quantity, signal.target)
                    self.active_limit_orders[signal.symbol] = limit_id
                    logger.info(f"PRE-TARGET PLACED: Sell Limit for {signal.symbol} @ {signal.target:.2f} (Order: {limit_id})")
                
                # 3. Place Market Stop Loss Order (NEW V6 PROTECT)
                if signal.stop_loss:
                    time.sleep(0.2)
                    sl_id = self.sell_slm.execute(signal.symbol, quantity, signal.stop_loss)
                    self.active_sl_orders[signal.symbol] = sl_id
                    logger.info(f"BROKER-SIDE SL PLACED: Sell SL-M for {signal.symbol} @ {signal.stop_loss:.2f} (Order: {sl_id})")
        except Exception as e:
            logger.error(f"Error in buy sequence: {e}")
    
    def _execute_sell(self, signal: Signal):
        """Execute sell order and immediately place target limit order."""
        positions = self.portfolio.get_positions()
        pos = positions.get(signal.symbol)
        
        is_exit_long = pos and pos.quantity > 0
        quantity = abs(pos.quantity) if is_exit_long else (signal.quantity or self._calculate_quantity(signal.symbol, signal.price))
        
        try:
            order_id = self.sell_action.execute(signal.symbol, quantity)
            logger.info(f"Live SELL MARKET order placed: {order_id} for {quantity} {signal.symbol}")
            
            if not is_exit_long and not pos:
                # 1. Store Security Targets
                self.security_targets[signal.symbol] = {
                    'sl': signal.stop_loss,
                    'tp': signal.target,
                    'be_trig': signal.breakeven_trigger,
                    'trail_trig': signal.partial_exit_trigger,
                    'be_moved': False,
                    'peak': signal.price
                }
                # 2. Place Limit Order for Target
                if signal.target:
                    time.sleep(0.5)
                    limit_id = self.buy_limit.execute(signal.symbol, quantity, signal.target)
                    self.active_limit_orders[signal.symbol] = limit_id
                    logger.info(f"PRE-TARGET PLACED: Buy Limit for {signal.symbol} @ {signal.target:.2f} (Order: {limit_id})")

                # 3. Place Market Stop Loss Order (NEW V6 PROTECT)
                if signal.stop_loss:
                    time.sleep(0.2)
                    sl_id = self.buy_slm.execute(signal.symbol, quantity, signal.stop_loss)
                    self.active_sl_orders[signal.symbol] = sl_id
                    logger.info(f"BROKER-SIDE SL PLACED: Buy SL-M for {signal.symbol} @ {signal.stop_loss:.2f} (Order: {sl_id})")
        except Exception as e:
            logger.error(f"Error in sell sequence: {e}")

    def _cancel_all_open_orders(self, symbol: str):
        """
        Fetches ALL open orders from Kite for the given symbol and cancels them.
        This fixes the 'Blindness' issue where manually modified orders were ignored.
        """
        try:
            logger.info(f"SMART EXIT: Scanning for open orders to cancel for {symbol}...")
            orders = self.kite.orders()
            pending_orders = [o for o in orders if o['tradingsymbol'] == symbol and o['status'] in ('OPEN', 'TRIGGER PENDING', 'AM O REQ RECEIVED')]
            
            if not pending_orders:
                logger.info(f"SMART EXIT: No open orders found for {symbol}.")
                return

            for order in pending_orders:
                oid = order['order_id']
                logger.info(f"SMART EXIT: Cancelling open order {oid} ({order['transaction_type']} {order['quantity']} @ {order['price']})")
                try:
                    self.kite.cancel_order(variety=self.kite.VARIETY_REGULAR, order_id=oid)
                except Exception as e:
                    logger.warning(f"Failed to cancel order {oid}: {e}")
            
            # Allow time for cancellations to process
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Error in _cancel_all_open_orders: {e}")

    def _execute_exit(self, signal: Signal):
        """Closes position, ensuring ALL open orders are cancelled first."""
        positions = self.portfolio.get_positions()
        pos = positions.get(signal.symbol)
        if not pos: 
            logger.info(f"SMART EXIT: No position found for {signal.symbol} during exit call. Ensuring order cleanup.")
            self._cancel_all_open_orders(signal.symbol)
            self._cleanup_tracking(signal.symbol)
            return
        
        # 1. SMART EXIT: Cancel ALL Open Orders for this symbol
        self._cancel_all_open_orders(signal.symbol)

        # 2. Fire Market Exit
        quantity = abs(pos.quantity)
        try:
            if pos.quantity > 0:
                res = self.sell_action.execute(signal.symbol, quantity)
            else:
                res = self.buy_action.execute(signal.symbol, quantity)
            logger.info(f"Live EXIT MARKET order placed for {signal.symbol} | Reason: {signal.reason}")
            self._cleanup_tracking(signal.symbol)
        except Exception as e:
            logger.error(f"Error executing live exit: {e}")

    def _cleanup_tracking(self, symbol: str):
        if symbol in self.security_targets: del self.security_targets[symbol]
        if symbol in self.active_limit_orders: del self.active_limit_orders[symbol]
        if symbol in self.active_sl_orders: del self.active_sl_orders[symbol]
    
    def _calculate_quantity(self, symbol: str, price: float) -> int:
        margins = self.portfolio.get_margins()
        available = margins.get('equity', {}).get('available', {}).get('live_balance', 0)
        base_capital = min(available, self.max_capital) if self.max_capital else available
        max_allocation = base_capital * self.strategy.leverage
        quantity = int(max_allocation // price)
        return max(1, quantity)
    
    def get_status(self) -> dict:
        positions = self.portfolio.get_positions()
        return {
            'positions': len(positions),
            'current_prices': self.current_prices,
            'active_targets': self.security_targets
        }

    def shutdown(self):
        """Passive Shutdown: Analyzes and reports open broker protection without canceling."""
        logger.info("SHUTDOWN: Commencing order analysis...")
        try:
            orders = self.kite.orders()
            current_symbols = list(self.security_targets.keys())
            if not current_symbols:
                current_symbols = list(set(list(self.active_limit_orders.keys()) + list(self.active_sl_orders.keys())))

            for symbol in current_symbols:
                symbol_orders = [o for o in orders if o['tradingsymbol'] == symbol and o['status'] in ('OPEN', 'TRIGGER PENDING')]
                if symbol_orders:
                    logger.info(f"SHUTDOWN STATUS [{symbol}]: {len(symbol_orders)} orders remain ACTIVE on Broker side.")
                    for o in symbol_orders:
                        logger.info(f"  - {o['transaction_type']} {o['order_type']} | Qty: {o['quantity']} | Price/Trig: {o['price'] or o['trigger_price']}")
                else:
                    logger.info(f"SHUTDOWN STATUS [{symbol}]: No active orders found.")
        except Exception as e:
            logger.error(f"Error during shutdown analysis: {e}")
        logger.info("SHUTDOWN: Process complete. Trade protection remains LIVE on Broker.")

    def sync_and_cleanup(self):
        """Standard Janitor: Runs even without ticks to ensure broker state vs local state parity."""
        if not self.security_targets: return
        self.check_security()

