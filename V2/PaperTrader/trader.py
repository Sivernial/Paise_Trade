from typing import Dict, List
from datetime import datetime
from .portfolio import PaperPortfolio
from Algorithms.base_strategy import BaseStrategy
from Common import Order, Signal, SignalType, TransactionType, OrderType, OrderStatus
from DataStream_Engine import DataStream
import logging

logger = logging.getLogger(__name__)

class PaperTrader:
    
    def __init__(self, strategy: BaseStrategy, initial_capital: float = 100000):
        self.strategy = strategy
        self.portfolio = PaperPortfolio(initial_capital)
        self.current_prices: Dict[str, float] = {}
    
    def on_tick(self, tick):
        symbol = tick.get('instrument_token')
        price = tick.get('last_price', 0)
        
        if symbol and price:
            self.current_prices[symbol] = price
    
    def process_signals(self, signals: List[Signal]):
        for signal in signals:
            if signal.signal_type == SignalType.BUY:
                self._execute_buy(signal)
            elif signal.signal_type == SignalType.SELL:
                self._execute_sell(signal)
    
    def _execute_buy(self, signal: Signal):
        quantity = signal.quantity or self._calculate_quantity(signal.symbol, signal.price)
        
        order = Order(
            symbol=signal.symbol,
            quantity=quantity,
            price=signal.price,
            order_type=OrderType.MARKET,
            transaction_type=TransactionType.BUY,
            timestamp=datetime.now(),
            status=OrderStatus.COMPLETE
        )
        
        if self.portfolio.execute_order(order, signal.price):
            logger.info(f"Paper buy executed: {quantity} {signal.symbol} @ {signal.price}")
    
    def _execute_sell(self, signal: Signal):
        if signal.symbol not in self.portfolio.positions:
            return
        
        pos = self.portfolio.positions[signal.symbol]
        quantity = signal.quantity or pos.quantity
        
        order = Order(
            symbol=signal.symbol,
            quantity=quantity,
            price=signal.price,
            order_type=OrderType.MARKET,
            transaction_type=TransactionType.SELL,
            timestamp=datetime.now(),
            status=OrderStatus.COMPLETE
        )
        
        if self.portfolio.execute_order(order, signal.price):
            logger.info(f"Paper sell executed: {quantity} {signal.symbol} @ {signal.price}")
    
    def _calculate_quantity(self, symbol: str, price: float) -> int:
        max_allocation = self.portfolio.cash * 0.1
        quantity = int(max_allocation / price)
        return max(1, quantity)
    
    def get_status(self) -> dict:
        total_value = self.portfolio.get_total_value(self.current_prices)
        return {
            'portfolio': self.portfolio.get_summary(),
            'total_value': total_value,
            'returns': (total_value - self.portfolio.initial_capital) / self.portfolio.initial_capital
        }

