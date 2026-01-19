"""
Common data models used across the trading system.
"""
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

class SignalType(Enum):
    """Signal types for trading actions."""
    BUY = "BUY"
    SELL = "SELL"
    EXIT = "EXIT"

class TransactionType(Enum):
    """Transaction types for order execution."""
    BUY = "BUY"
    SELL = "SELL"

@dataclass
class Signal:
    """Represents a trading signal."""
    symbol: str
    signal_type: SignalType
    price: float
    timestamp: datetime
    quantity: int = 0
    reason: str = ""

@dataclass
class Position:
    """Represents an open trading position."""
    symbol: str
    quantity: int
    entry_price: float
    entry_date: datetime
    current_price: float = 0.0
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    realized_pnl: float = 0.0
    
    @property
    def unrealized_pnl(self) -> float:
        """Calculate unrealized P&L."""
        if self.quantity > 0:  # Long position
            return (self.current_price - self.entry_price) * self.quantity
        else:  # Short position
            return (self.entry_price - self.current_price) * abs(self.quantity)
    
    @property
    def total_pnl(self) -> float:
        """Calculate total P&L (realized + unrealized)."""
        return self.realized_pnl + self.unrealized_pnl
