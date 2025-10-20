"""
Dataclasses for Portfolio Management
Contains all data structures used in the portfolio management module
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

class PositionType(Enum):
    LONG = "LONG"
    SHORT = "SHORT"

@dataclass
class Position:
    """Enhanced position tracking"""
    symbol: str
    position_type: PositionType
    quantity: int
    entry_price: float
    entry_date: datetime
    current_price: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_stop: Optional[float] = None
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    commission_paid: float = 0.0
    
    def __post_init__(self):
        self.market_value = self.quantity * self.current_price
        self.cost_basis = self.quantity * self.entry_price
    
    def update_price(self, new_price: float):
        """Update current price and calculate unrealized P&L"""
        self.current_price = new_price
        self.market_value = self.quantity * new_price
        
        if self.position_type == PositionType.LONG:
            self.unrealized_pnl = (new_price - self.entry_price) * self.quantity
        else:  # SHORT
            self.unrealized_pnl = (self.entry_price - new_price) * self.quantity
    
    def get_return_pct(self) -> float:
        """Get percentage return on position"""
        if self.cost_basis == 0:
            return 0.0
        return (self.unrealized_pnl / self.cost_basis) * 100
    
    def days_held(self) -> int:
        """Number of days position has been held"""
        return (datetime.now() - self.entry_date).days

@dataclass
class PortfolioMetrics:
    """Portfolio performance metrics"""
    total_value: float = 0.0
    cash: float = 0.0
    invested_value: float = 0.0
    total_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    day_pnl: float = 0.0
    total_return_pct: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    open_positions: int = 0
    sector_allocation: Dict[str, float] = field(default_factory=dict)