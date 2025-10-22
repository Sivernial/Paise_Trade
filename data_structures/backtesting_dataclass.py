"""
Dataclasses for Backtesting Engine
Contains all data structures used in the backtesting module
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict
from .common import OrderType, OrderStatus, Position, Order

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