"""
Data Structures Package for Paise Trade
Centralized location for all data structures used across the trading system
"""

# Import all dataclasses for easy access
from .backtesting_dataclass import (
    Order as BacktestOrder,
    Position as BacktestPosition,
    PerformanceMetrics,
    OrderType as BacktestOrderType,
    OrderStatus as BacktestOrderStatus
)

from .trading_dataclass import (
    Order as TradingOrder,
    OrderType,
    OrderStatus,
    TransactionType,
    ProductType
)

from .strategy_dataclass import (
    Signal,
    SignalType
)

from .portfolio_dataclass import (
    PortfolioMetrics
)

from .common import (
    Position,
    PositionType,
    Order,
    OrderType,
    OrderStatus
)

from .config_dataclass import (
    TradingConfig,
    StrategyConfig,
    APIConfig,
    BacktestConfig
)

__all__ = [
    # Backtesting
    'BacktestOrder',
    'BacktestPosition', 
    'PerformanceMetrics',
    'BacktestOrderType',
    'BacktestOrderStatus',
    
    # Trading
    'TradingOrder',
    'OrderType',
    'OrderStatus',
    'TransactionType',
    'ProductType',
    
    # Strategy
    'Signal',
    'SignalType',
    
    # Portfolio
    'Position',
    'PortfolioMetrics',
    'PositionType',
    
    # Common
    'Order',
    
    # Configuration
    'TradingConfig',
    'StrategyConfig',
    'APIConfig',
    'BacktestConfig'
]