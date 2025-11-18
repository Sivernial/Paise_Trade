"""
Shared Enums and Constants for Trading System
Consolidates common enumerations used across multiple modules
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

# Order-related enums
class OrderType(Enum):
    """Unified order type for both backtesting and live trading"""
    # Basic order types
    BUY = "BUY"
    SELL = "SELL"
    
    # Advanced order types (for live trading)
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "SL"
    STOP_LOSS_MARKET = "SL-M"

class OrderStatus(Enum):
    """Unified order status for both backtesting and live trading"""
    PENDING = "PENDING"
    OPEN = "OPEN"
    FILLED = "FILLED"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class TransactionType(Enum):
    """Transaction direction"""
    BUY = "BUY"
    SELL = "SELL"

class ProductType(Enum):
    """Product types for live trading"""
    CNC = "CNC"  # Cash and Carry
    MIS = "MIS"  # Margin Intraday Squareoff
    NRML = "NRML"  # Normal

# Position-related enums
class PositionType(Enum):
    """Position direction"""
    LONG = "LONG"
    SHORT = "SHORT"

# Signal-related enums
class SignalType(Enum):
    """Trading signal types"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

@dataclass
class Position:
    """
    Unified position class for both backtesting and portfolio management
    
    Combines features from both contexts to avoid duplication
    """
    symbol: str
    quantity: int
    entry_price: float
    entry_date: datetime  # Renamed from entry_timestamp for consistency
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    
    # Portfolio management features (optional)
    position_type: PositionType = PositionType.LONG
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_stop: Optional[float] = None
    commission_paid: float = 0.0
    
    # Calculated fields
    market_value: float = 0.0
    cost_basis: float = 0.0
    
    def __post_init__(self):
        """Initialize calculated fields"""
        self.market_value = self.quantity * self.current_price
        self.cost_basis = self.quantity * self.entry_price
        
        # Calculate unrealized P&L based on position type
        if self.position_type == PositionType.LONG:
            self.unrealized_pnl = (self.current_price - self.entry_price) * self.quantity
        else:  # SHORT
            self.unrealized_pnl = (self.entry_price - self.current_price) * self.quantity
    
    def update_price(self, new_price: float):
        """Update current price and recalculate P&L"""
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
    
    @property
    def entry_timestamp(self) -> datetime:
        """Backward compatibility property for backtesting"""
        return self.entry_date

@dataclass 
class Order:
    """
    Unified order class for both backtesting and live trading
    
    Combines features from both contexts with optional fields
    """
    symbol: str
    quantity: int
    price: float
    order_type: OrderType
    timestamp: datetime
    order_id: str = ""
    status: OrderStatus = OrderStatus.PENDING
    
    # Live trading specific fields (optional)
    exchange: str = "NSE"
    transaction_type: Optional[TransactionType] = None
    product_type: ProductType = ProductType.MIS
    tag: str = ""
    
    # Execution details
    fill_price: float = 0.0
    fill_timestamp: Optional[datetime] = None
    filled_quantity: int = 0
    average_price: float = 0.0
    commission: float = 0.0
    update_timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize default values and derive missing fields"""
        if self.timestamp is None:
            self.timestamp = datetime.now()
            
        # Derive transaction_type from order_type for backward compatibility
        if self.transaction_type is None:
            if self.order_type in [OrderType.BUY]:
                self.transaction_type = TransactionType.BUY
            elif self.order_type in [OrderType.SELL]:
                self.transaction_type = TransactionType.SELL
    
    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled"""
        return self.status in [OrderStatus.FILLED, OrderStatus.COMPLETE]
    
    @property
    def remaining_quantity(self) -> int:
        """Get remaining unfilled quantity"""
        return max(0, self.quantity - self.filled_quantity)

# Trading constants
class TradingConstants:
    """Common trading constants"""
    DEFAULT_COMMISSION_RATE = 0.001  # 0.1%
    DEFAULT_SLIPPAGE_RATE = 0.0005   # 0.05%
    DEFAULT_INITIAL_CAPITAL = 100000  # 1 Lakh
    DEFAULT_MAX_POSITIONS = 10
    DEFAULT_RISK_FREE_RATE = 0.06    # 6%
    
    # Date formats
    DATE_FORMAT = "%Y-%m-%d"
    DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    # Risk management defaults
    DEFAULT_STOP_LOSS_PCT = 0.03     # 3%
    DEFAULT_TAKE_PROFIT_PCT = 0.12   # 12%
    DEFAULT_MAX_DAILY_LOSS_PCT = 0.03 # 3%
    DEFAULT_MAX_POSITION_SIZE_PCT = 0.1 # 10%

# Market timings (IST)
class MarketTimings:
    """Indian market timings"""
    MARKET_OPEN = "09:15"
    MARKET_CLOSE = "15:30"
    PRE_MARKET_OPEN = "09:00"
    PRE_MARKET_CLOSE = "09:15"
    POST_MARKET_OPEN = "15:40"
    POST_MARKET_CLOSE = "16:00"

# Common exchanges
class Exchange(Enum):
    """Supported exchanges"""
    NSE = "NSE"
    BSE = "BSE"
    MCX = "MCX"
    NCDEX = "NCDEX"