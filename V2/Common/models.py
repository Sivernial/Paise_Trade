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

@dataclass
class Signal:
    symbol: str
    signal_type: SignalType
    price: float
    timestamp: datetime
    confidence: float = 0.0
    reason: str = ""
    quantity: int = 0

@dataclass
class Candle:
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int

