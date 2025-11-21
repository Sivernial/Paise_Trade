from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from .enums import OrderType, OrderStatus, TransactionType, ProductType, SignalType

@dataclass
class Order:
    symbol: str
    quantity: int
    price: float
    order_type: OrderType
    transaction_type: TransactionType
    timestamp: datetime = field(default_factory=datetime.now)
    order_id: str = ""
    status: OrderStatus = OrderStatus.PENDING
    exchange: str = "NSE"
    product_type: ProductType = ProductType.MIS
    filled_quantity: int = 0
    average_price: float = 0.0
    commission: float = 0.0

@dataclass
class Position:
    symbol: str
    quantity: int
    entry_price: float
    entry_date: datetime
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    # Position Management Fields
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    trailing_stop: Optional[float] = None
    breakeven_trigger: Optional[float] = None
    partial_exit_trigger: Optional[float] = None
    partial_exit_done: bool = False  # Track if partial exit already executed
    breakeven_moved: bool = False    # Track if stop moved to breakeven
    highest_price: float = 0.0       # Track highest price for trailing stop
    lowest_price: float = float('inf')  # Track lowest price for trailing stop (shorts)

@dataclass
class Signal:
    symbol: str
    signal_type: SignalType
    price: float
    timestamp: datetime
    confidence: float = 0.0
    reason: str = ""
    quantity: int = 0
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    trailing_stop: Optional[float] = None
    breakeven_trigger: Optional[float] = None  # Price at which to move stop to breakeven
    partial_exit_trigger: Optional[float] = None  # Price at which to take partial profits

@dataclass
class Candle:
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int

