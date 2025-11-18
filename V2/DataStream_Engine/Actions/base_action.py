from abc import ABC, abstractmethod
from kiteconnect import KiteConnect
from Common import Order, TransactionType, OrderType
import logging

logger = logging.getLogger(__name__)

class BaseAction(ABC):
    
    def __init__(self, kite: KiteConnect):
        self.kite = kite
    
    @abstractmethod
    def execute(self, symbol: str, quantity: int, **kwargs) -> str:
        pass
    
    def validate_order(self, symbol: str, quantity: int, price: float = None):
        if not symbol or quantity <= 0:
            raise ValueError("Invalid order parameters")
        if price is not None and price <= 0:
            raise ValueError("Invalid price")

