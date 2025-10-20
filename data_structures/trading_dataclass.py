"""
Dataclasses for Trading Engine
Contains all data structures used in the trading engine module
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "SL"
    STOP_LOSS_MARKET = "SL-M"

class OrderStatus(Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class TransactionType(Enum):
    BUY = "BUY"
    SELL = "SELL"

class ProductType(Enum):
    CNC = "CNC"  # Cash and Carry
    MIS = "MIS"  # Margin Intraday Squareoff
    NRML = "NRML"  # Normal

@dataclass
class Order:
    """Enhanced order representation"""
    symbol: str
    exchange: str
    transaction_type: TransactionType
    quantity: int
    price: float
    order_type: OrderType
    product_type: ProductType
    order_id: str = ""
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    average_price: float = 0.0
    timestamp: datetime = None
    update_timestamp: datetime = None
    tag: str = ""
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()