"""
Portfolio management for paper trading.
Handles positions, cash, and P&L tracking.
"""
from typing import Dict
from datetime import datetime
import logging
from ..common.models import Position

logger = logging.getLogger(__name__)

class Portfolio:
    """Manages trading positions and cash balance."""
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.trade_history = []
        
    def get_position(self, symbol: str) -> Position:
        """Get position for a symbol."""
        return self.positions.get(symbol)
    
    def get_positions(self) -> Dict[str, Position]:
        """Get all open positions."""
        return self.positions
    
    def add_position(self, symbol: str, quantity: int, price: float, timestamp: datetime):
        """Open a new position."""
        if symbol in self.positions:
            logger.warning(f"Position already exists for {symbol}")
            return False
        
        cost = abs(quantity) * price
        if cost > self.cash:
            logger.warning(f"Insufficient cash for {symbol}: need {cost}, have {self.cash}")
            return False
        
        self.positions[symbol] = Position(
            symbol=symbol,
            quantity=quantity,
            entry_price=price,
            entry_date=timestamp,
            current_price=price
        )
        
        # Deduct cash for longs, credit for shorts
        if quantity > 0:
            self.cash -= cost
        else:
            self.cash += cost
        
        logger.info(f"Opened position: {symbol} x {quantity} @ {price}")
        return True
    
    def close_position(self, symbol: str, price: float, timestamp: datetime) -> float:
        """Close an existing position and return P&L."""
        if symbol not in self.positions:
            logger.warning(f"No position to close for {symbol}")
            return 0.0
        
        pos = self.positions[symbol]
        pnl = 0.0
        
        if pos.quantity > 0:  # Long position
            pnl = (price - pos.entry_price) * pos.quantity
            self.cash += pos.quantity * price
        else:  # Short position
            pnl = (pos.entry_price - price) * abs(pos.quantity)
            self.cash -= abs(pos.quantity) * price
        
        self.trade_history.append({
            'symbol': symbol,
            'entry_date': pos.entry_date,
            'exit_date': timestamp,
            'entry_price': pos.entry_price,
            'exit_price': price,
            'quantity': pos.quantity,
            'pnl': pnl
        })
        
        del self.positions[symbol]
        logger.info(f"Closed position: {symbol}, PnL: {pnl:.2f}")
        return pnl
    
    def update_prices(self, prices: Dict[str, float]):
        """Update current prices for all positions."""
        for symbol, pos in self.positions.items():
            if symbol in prices:
                pos.current_price = prices[symbol]
    
    def get_total_value(self) -> float:
        """Calculate total portfolio value (cash + positions)."""
        position_value = sum(
            pos.quantity * pos.current_price if pos.quantity > 0 
            else -abs(pos.quantity) * pos.current_price
            for pos in self.positions.values()
        )
        return self.cash + position_value
    
    def get_pnl(self) -> float:
        """Get total P&L."""
        return self.get_total_value() - self.initial_capital
