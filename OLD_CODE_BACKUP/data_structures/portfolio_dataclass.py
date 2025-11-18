"""
Dataclasses for Portfolio Management
Contains all data structures used in the portfolio management module
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional
from .common import Position

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