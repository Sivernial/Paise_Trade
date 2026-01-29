from typing import Dict, Optional
from Common import Position, Order, TransactionType, Signal
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PaperPortfolio:
    
    def __init__(self, initial_capital: float = 100000, leverage: float = 1.0):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.leverage = leverage
        self.positions: Dict[str, Position] = {}
        self.orders: list = []
    
    def get_positions(self) -> Dict[str, Position]:
        """Return the current active positions."""
        return self.positions
    
    def execute_order(self, order: Order, current_price: float, signal: Optional[Signal] = None):
        """Execute a buy or sell order, supporting short selling and leverage."""
        
        # Determine quantity delta
        is_buy = order.transaction_type == TransactionType.BUY
        qty_delta = order.quantity if is_buy else -order.quantity
        transaction_amount = order.quantity * current_price
        
        # Margin Management (V6 Leverage Support)
        # Equity = Cash + Unrealized PnL of all positions
        total_unrealized_pnl = sum([pos.unrealized_pnl for pos in self.positions.values()])
        equity = self.cash + total_unrealized_pnl
        
        # Used Margin = Total Open Value / Leverage
        current_open_value = sum([abs(pos.quantity) * pos.current_price for pos in self.positions.values()])
        used_margin = current_open_value / self.leverage
        
        # New Margin Required for this trade
        new_margin_required = transaction_amount / self.leverage
        
        # Buying Power Check
        # We only check margin if we are INCREASING a position or opening a new one.
        # If we are closing/reducing, we don't need margin check.
        is_opening_or_increasing = False
        if order.symbol not in self.positions:
            is_opening_or_increasing = True
        else:
            pos = self.positions[order.symbol]
            if (is_buy and pos.quantity >= 0) or (not is_buy and pos.quantity <= 0):
                is_opening_or_increasing = True
        
        if is_opening_or_increasing:
            if (used_margin + new_margin_required) > equity:
                 logger.warning(f"Insufficient funds (Margin) for {order.transaction_type.value}: need {new_margin_required:.2f} margin, current used: {used_margin:.2f}, equity: {equity:.2f}")
                 return False
        
        # Cash management: Substracting full amount to keep PnL math simple
        # Note: self.cash can go negative, but Total Value (Cash + Values) will be correct.
        if is_buy:
            self.cash -= transaction_amount
        else:
            self.cash += transaction_amount

        if order.symbol in self.positions:
            pos = self.positions[order.symbol]
            
            # If closing or reducing a position, calculate realized PnL
            if (is_buy and pos.quantity < 0) or (not is_buy and pos.quantity > 0):
                # We are closing or reversing
                qty_closed = min(abs(pos.quantity), order.quantity)
                if pos.quantity > 0: # Closing a long
                    pnl = (current_price - pos.entry_price) * qty_closed
                else: # Closing a short (covering)
                    pnl = (pos.entry_price - current_price) * qty_closed
                pos.realized_pnl += pnl
                logger.info(f"PnL Realized for {order.symbol}: {pnl:.2f}")

            # Update Entry Price (Weighted Average for increasing)
            if (is_buy and pos.quantity >= 0) or (not is_buy and pos.quantity <= 0):
                 total_cost = abs(pos.quantity) * pos.entry_price + order.quantity * current_price
                 total_qty = abs(pos.quantity) + order.quantity
                 pos.entry_price = total_cost / total_qty if total_qty != 0 else current_price
            
            # Capture data for trade recording if we closing
            entry_date = pos.entry_date
            entry_price = pos.entry_price

            pos.quantity += qty_delta
            
            if pos.quantity == 0:
                logger.info(f"Position closed for {order.symbol}. Total Realized PnL: {pos.realized_pnl:.2f}")
                del self.positions[order.symbol]
        else:
            # Create new position (long or short)
            pos = Position(
                symbol=order.symbol,
                quantity=qty_delta,
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
            self.positions[order.symbol] = pos
            qty_closed = 0
        
        self.orders.append(order)

        # Return trade info if PnL was realized (for database logging)
        if 'pnl' in locals() and pnl != 0:
            return {
                'symbol': order.symbol,
                'entry_time': entry_date,
                'exit_time': datetime.now(),
                'entry_price': entry_price,
                'exit_price': current_price,
                'quantity': qty_closed,
                'side': 'SELL' if not is_buy else 'BUY',
                'pnl': pnl,
                'mode': 'paper'
            }
        
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
        # Create readable positions summary
        pos_summary = {
            sym: f"{pos.quantity} @ {pos.entry_price:.2f}" 
            for sym, pos in self.positions.items()
        }
        return {
            'cash': self.cash,
            'num_positions': len(self.positions),
            'total_orders': len(self.orders),
            'positions': pos_summary # Added
        }

