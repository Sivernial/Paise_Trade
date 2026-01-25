from typing import Dict, List
from datetime import datetime
from kiteconnect import KiteConnect
from .portfolio import LivePortfolio
from Algorithms.base_strategy import BaseStrategy
from Common import Signal, SignalType
from DataStream_Engine import BuyInstant, SellInstant, BuyLimit, SellLimit
import logging

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
        self.current_prices: Dict[str, float] = {}
        self.security_targets: Dict[str, Dict[str, float]] = {} # Tracks SL/TP
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
        Polls current prices against SL/TP targets on every tick.
        """
        if not self.security_targets: return
        
        # We need the current net positions to see what's actually open
        positions = self.portfolio.get_positions()
        
        for symbol, targets in list(self.security_targets.items()):
            price = self.current_prices.get(symbol)
            if not price: continue
            
            # If position no longer exists in Kite, clear targets
            if symbol not in positions:
                del self.security_targets[symbol]
                continue
                
            pos = positions[symbol]
            is_long = pos.quantity > 0
            
            sl = targets.get('sl')
            tp = targets.get('tp')
            
            # Check Stop Loss
            hit_sl = False
            if sl:
                if is_long and price <= sl: hit_sl = True
                elif not is_long and price >= sl: hit_sl = True
                
            if hit_sl:
                reason = f"LIVE SECURITY EXIT: Stop Loss hit at {price:.2f} (Target: {sl:.2f})"
                logger.warning(reason)
                self._execute_exit(Signal(symbol, SignalType.EXIT, price, datetime.now(), 0, reason))
                continue

            # Check Profit Target
            hit_tp = False
            if tp:
                if is_long and price >= tp: hit_tp = True
                elif not is_long and price <= tp: hit_tp = True
                
            if hit_tp:
                reason = f"LIVE SECURITY EXIT: Profit Target hit at {price:.2f} (Target: {tp:.2f})"
                logger.info(reason)
                self._execute_exit(Signal(symbol, SignalType.EXIT, price, datetime.now(), 0, reason))
    
    def _execute_buy(self, signal: Signal):
        """Execute buy order, handling both new longs and short coverings."""
        positions = self.portfolio.get_positions()
        pos = positions.get(signal.symbol)
        
        # Check if we're covering a short position
        is_cover = pos and pos.quantity < 0 and signal.quantity <= 0
        use_limit = is_cover and "Profit Target" in signal.reason
        
        if is_cover:
            quantity = abs(pos.quantity)
            logger.info(f"Covering SHORT position in LIVE: {signal.symbol} Qty: {quantity} | Reason: {signal.reason}")
        else:
            quantity = signal.quantity or self._calculate_quantity(signal.symbol, signal.price)
        
        try:
            if use_limit:
                order_id = self.buy_limit.execute(signal.symbol, quantity, signal.price)
                logger.info(f"Live BUY LIMIT order placed: {order_id} for {quantity} {signal.symbol} @ {signal.price}")
            else:
                order_id = self.buy_action.execute(signal.symbol, quantity)
                logger.info(f"Live BUY MARKET order placed: {order_id} for {quantity} {signal.symbol}")
            
            # Store SL/TP for the new position (only if not a cover)
            if not is_cover and (signal.stop_loss or signal.target):
                self.security_targets[signal.symbol] = {
                    'sl': signal.stop_loss,
                    'tp': signal.target
                }
        except Exception as e:
            logger.error(f"Error placing buy order: {e}")
    
    def _execute_sell(self, signal: Signal):
        """Execute sell order, handling both new shorts and long exits."""
        positions = self.portfolio.get_positions()
        pos = positions.get(signal.symbol)
        
        # Check if we're exiting a long position
        is_exit_long = pos and pos.quantity > 0 and signal.quantity <= 0
        use_limit = is_exit_long and "Profit Target" in signal.reason
        
        if is_exit_long:
            quantity = abs(pos.quantity)
            logger.info(f"Exiting LONG position in LIVE: {signal.symbol} Qty: {quantity} | Reason: {signal.reason}")
        else:
            quantity = signal.quantity or self._calculate_quantity(signal.symbol, signal.price)
        
        try:
            if use_limit:
                order_id = self.sell_limit.execute(signal.symbol, quantity, signal.price)
                logger.info(f"Live SELL LIMIT order placed: {order_id} for {quantity} {signal.symbol} @ {signal.price}")
            else:
                order_id = self.sell_action.execute(signal.symbol, quantity)
                logger.info(f"Live SELL MARKET order placed: {order_id} for {quantity} {signal.symbol}")
            
            # Store SL/TP for the new position (only if it's a new short entry)
            if not is_exit_long and not pos and (signal.stop_loss or signal.target):
                self.security_targets[signal.symbol] = {
                    'sl': signal.stop_loss,
                    'tp': signal.target
                }
        except Exception as e:
            logger.error(f"Error placing sell order: {e}")

    def _execute_exit(self, signal: Signal):
        """Closes an existing position."""
        positions = self.portfolio.get_positions()
        pos = positions.get(signal.symbol)
        if not pos: return
        
        quantity = abs(pos.quantity)
        use_limit = "Profit Target" in signal.reason
        
        try:
            if pos.quantity > 0:
                if use_limit:
                    res = self.sell_limit.execute(signal.symbol, quantity, signal.price)
                    logger.info(f"Live EXIT LIMIT order placed: {res} for {quantity} {signal.symbol} @ {signal.price} | Reason: {signal.reason}")
                else:
                    res = self.sell_action.execute(signal.symbol, quantity)
                    logger.info(f"Live EXIT MARKET order placed: {res} for {quantity} {signal.symbol} | Reason: {signal.reason}")
            else:
                if use_limit:
                    res = self.buy_limit.execute(signal.symbol, quantity, signal.price)
                    logger.info(f"Live EXIT LIMIT order placed: {res} for {quantity} {signal.symbol} @ {signal.price} | Reason: {signal.reason}")
                else:
                    res = self.buy_action.execute(signal.symbol, quantity)
                    logger.info(f"Live EXIT MARKET order placed: {res} for {quantity} {signal.symbol} | Reason: {signal.reason}")
            
            # Clear targets
            if signal.symbol in self.security_targets:
                del self.security_targets[signal.symbol]
        except Exception as e:
            logger.error(f"Error executing live exit: {e}")
    
    def _calculate_quantity(self, symbol: str, price: float) -> int:
        margins = self.portfolio.get_margins()
        available = margins.get('equity', {}).get('available', {}).get('live_balance', 0)
        
        # Use either available balance or the user-defined cap
        base_capital = min(available, self.max_capital) if self.max_capital else available
        
        max_allocation = base_capital * self.strategy.leverage
        quantity = int(max_allocation // price)
        return max(1, quantity)
    
    def get_status(self) -> dict:
        positions = self.portfolio.get_positions()
        margins = self.portfolio.get_margins()
        
        return {
            'positions': len(positions),
            'margins': margins.get('equity', {}),
            'current_prices': self.current_prices
        }

