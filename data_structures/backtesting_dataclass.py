"""
Dataclasses for Backtesting Engine
Contains all data structures used in the backtesting module
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict

class OrderType(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderStatus(Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"

@dataclass
class Order:
    """Represents a trading order"""
    symbol: str
    order_type: OrderType
    quantity: int
    price: float
    timestamp: datetime
    order_id: str = ""
    status: OrderStatus = OrderStatus.PENDING
    fill_price: float = 0.0
    fill_timestamp: Optional[datetime] = None
    commission: float = 0.0

@dataclass
class Position:
    """Represents a trading position"""
    symbol: str
    quantity: int
    entry_price: float
    entry_timestamp: datetime
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0

@dataclass
class PerformanceMetrics:
    """Portfolio performance metrics"""
    total_return: float = 0.0
    annualized_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    profitable_trades: int = 0
    losing_trades: int = 0
    avg_trade_return: float = 0.0
    avg_winning_trade: float = 0.0
    avg_losing_trade: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    calmar_ratio: float = 0.0
    sortino_ratio: float = 0.0