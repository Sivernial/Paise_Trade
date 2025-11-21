from typing import Dict, Optional
from Common import Position, Order, TransactionType, Signal
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PaperPortfolio:
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.orders: list = []
    
    def execute_order(self, order: Order, current_price: float, signal: Optional[Signal] = None):
        
        if order.transaction_type == TransactionType.BUY:
            cost = order.quantity * current_price
            if cost > self.cash:
                logger.warning(f"Insufficient funds: need {cost}, have {self.cash}")
                return False
            
            self.cash -= cost
            
            if order.symbol in self.positions:
                pos = self.positions[order.symbol]
                total_cost = pos.quantity * pos.entry_price + order.quantity * current_price
                total_qty = pos.quantity + order.quantity
                pos.entry_price = total_cost / total_qty
                pos.quantity = total_qty
            else:
                # Create new position with position management from signal
                self.positions[order.symbol] = Position(
                    symbol=order.symbol,
                    quantity=order.quantity,
                    entry_price=current_price,
                    entry_date=datetime.now(),
                    current_price=current_price,
                    highest_price=current_price,
                    lowest_price=current_price,
                    stop_loss=signal.stop_loss if signal else None,
                    target=signal.target if signal else None,
                    trailing_stop=signal.trailing_stop if signal else None,
                    breakeven_trigger=signal.breakeven_trigger if signal else None,
                    partial_exit_trigger=signal.partial_exit_trigger if signal else None
                )
        
        elif order.transaction_type == TransactionType.SELL:
            if order.symbol not in self.positions:
                logger.warning(f"No position to sell: {order.symbol}")
                return False
            
            pos = self.positions[order.symbol]
            if pos.quantity < order.quantity:
                logger.warning(f"Insufficient quantity: need {order.quantity}, have {pos.quantity}")
                return False
            
            proceeds = order.quantity * current_price
            self.cash += proceeds
            
            # Calculate realized PnL
            pnl = (current_price - pos.entry_price) * order.quantity
            pos.realized_pnl += pnl
            
            pos.quantity -= order.quantity
            if pos.quantity == 0:
                logger.info(f"Position closed: {order.symbol}, Realized PnL: {pos.realized_pnl:.2f}")
                del self.positions[order.symbol]
        
        self.orders.append(order)
        return True
    
    def update_position_prices(self, symbol: str, current_price: float):
        if symbol in self.positions:
            pos = self.positions[symbol]
            pos.current_price = current_price
            pos.highest_price = max(pos.highest_price, current_price)
            pos.lowest_price = min(pos.lowest_price, current_price)
            pos.unrealized_pnl = (current_price - pos.entry_price) * pos.quantity
    
    def check_partial_exit(self, symbol: str, partial_exit_pct: float = 0.5) -> Optional[int]:
        if symbol not in self.positions:
            return None
        
        pos = self.positions[symbol]
        
        # Already did partial exit
        if pos.partial_exit_done:
            return None
        
        # No partial exit trigger set
        if pos.partial_exit_trigger is None:
            return None
        
        # Check if price reached partial exit trigger (works for both longs and shorts)
        # For longs: current_price >= trigger
        # For shorts: current_price <= trigger
        is_long = pos.quantity > 0
        
        if is_long and pos.current_price >= pos.partial_exit_trigger:
            exit_qty = int(pos.quantity * partial_exit_pct)
            pos.partial_exit_done = True
            logger.info(f"Partial exit triggered for {symbol}: {exit_qty} shares at {pos.current_price}")
            return exit_qty
        elif not is_long and pos.current_price <= pos.partial_exit_trigger:
            exit_qty = int(abs(pos.quantity) * partial_exit_pct)
            pos.partial_exit_done = True
            logger.info(f"Partial exit triggered for {symbol}: {exit_qty} shares at {pos.current_price}")
            return exit_qty
        
        return None
    
    def check_breakeven_stop(self, symbol: str):
        if symbol not in self.positions:
            return
        
        pos = self.positions[symbol]
        
        # Already moved to breakeven
        if pos.breakeven_moved:
            return
        
        # No breakeven trigger set
        if pos.breakeven_trigger is None:
            return
        
        is_long = pos.quantity > 0
        
        # Check if price reached breakeven trigger
        if is_long and pos.current_price >= pos.breakeven_trigger:
            pos.stop_loss = pos.entry_price
            pos.breakeven_moved = True
            logger.info(f"Breakeven stop set for {symbol} at {pos.entry_price}")
        elif not is_long and pos.current_price <= pos.breakeven_trigger:
            pos.stop_loss = pos.entry_price
            pos.breakeven_moved = True
            logger.info(f"Breakeven stop set for {symbol} at {pos.entry_price}")
    
    def update_trailing_stop(self, symbol: str, trail_atr_mult: float, current_atr: float):
        if symbol not in self.positions:
            return
        
        pos = self.positions[symbol]
        
        if pos.trailing_stop is None:
            return
        
        is_long = pos.quantity > 0
        
        if is_long:
            # For longs: stop = highest_high - trail_atr_mult * ATR
            new_trail = pos.highest_price - (trail_atr_mult * current_atr)
            # Only move stop up, never down
            if pos.stop_loss is not None:
                pos.stop_loss = max(pos.stop_loss, new_trail)
            else:
                pos.stop_loss = new_trail
        else:
            # For shorts: stop = lowest_low + trail_atr_mult * ATR
            new_trail = pos.lowest_price + (trail_atr_mult * current_atr)
            # Only move stop down, never up
            if pos.stop_loss is not None:
                pos.stop_loss = min(pos.stop_loss, new_trail)
            else:
                pos.stop_loss = new_trail
    
    def check_stop_loss(self, symbol: str) -> bool:
        """Check if stop loss is hit"""
        if symbol not in self.positions:
            return False
        
        pos = self.positions[symbol]
        
        if pos.stop_loss is None:
            return False
        
        is_long = pos.quantity > 0
        
        # For longs: exit if current_price <= stop_loss
        # For shorts: exit if current_price >= stop_loss
        if is_long and pos.current_price <= pos.stop_loss:
            logger.info(f"Stop loss hit for {symbol}: {pos.current_price} <= {pos.stop_loss}")
            return True
        elif not is_long and pos.current_price >= pos.stop_loss:
            logger.info(f"Stop loss hit for {symbol}: {pos.current_price} >= {pos.stop_loss}")
            return True
        
        return False
    
    def check_target(self, symbol: str) -> bool:
        if symbol not in self.positions:
            return False
        
        pos = self.positions[symbol]
        
        if pos.target is None:
            return False
        
        is_long = pos.quantity > 0
        
        # For longs: exit if current_price >= target
        # For shorts: exit if current_price <= target
        if is_long and pos.current_price >= pos.target:
            logger.info(f"Target hit for {symbol}: {pos.current_price} >= {pos.target}")
            return True
        elif not is_long and pos.current_price <= pos.target:
            logger.info(f"Target hit for {symbol}: {pos.current_price} <= {pos.target}")
            return True
        
        return False
    
    def get_total_value(self, current_prices: Dict[str, float]) -> float:
        value = self.cash
        for symbol, pos in self.positions.items():
            price = current_prices.get(symbol, pos.entry_price)
            value += pos.quantity * price
        return value
    
    def get_summary(self) -> dict:
        return {
            'cash': self.cash,
            'num_positions': len(self.positions),
            'total_orders': len(self.orders)
        }

