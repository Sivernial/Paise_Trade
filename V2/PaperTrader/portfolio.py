from typing import Dict
from Common import Position, Order, TransactionType
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PaperPortfolio:
    
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.orders: list = []
    
    def execute_order(self, order: Order, current_price: float):
        
        if order.transaction_type == TransactionType.BUY:
            cost = order.quantity * current_price
            if cost > self.cash:
                logger.warning(f"Insufficient funds: need {cost}, have {self.cash}")
                return False
            
            self.cash -= cost
            
            if order.symbol in self.positions:
                pos = self.positions[order.symbol]
                total_cost = pos.quantity * pos.entry_price + order.quantity * current_price
                total_qty = pos.quantity + order.quantity
                pos.entry_price = total_cost / total_qty
                pos.quantity = total_qty
            else:
                self.positions[order.symbol] = Position(
                    symbol=order.symbol,
                    quantity=order.quantity,
                    entry_price=current_price,
                    entry_date=datetime.now(),
                    current_price=current_price
                )
        
        elif order.transaction_type == TransactionType.SELL:
            if order.symbol not in self.positions:
                logger.warning(f"No position to sell: {order.symbol}")
                return False
            
            pos = self.positions[order.symbol]
            if pos.quantity < order.quantity:
                logger.warning(f"Insufficient quantity: need {order.quantity}, have {pos.quantity}")
                return False
            
            proceeds = order.quantity * current_price
            self.cash += proceeds
            
            pos.quantity -= order.quantity
            if pos.quantity == 0:
                del self.positions[order.symbol]
        
        self.orders.append(order)
        return True
    
    def get_total_value(self, current_prices: Dict[str, float]) -> float:
        value = self.cash
        for symbol, pos in self.positions.items():
            price = current_prices.get(symbol, pos.entry_price)
            value += pos.quantity * price
        return value
    
    def get_summary(self) -> dict:
        return {
            'cash': self.cash,
            'num_positions': len(self.positions),
            'total_orders': len(self.orders)
        }

