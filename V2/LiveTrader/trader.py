from typing import Dict, List
from datetime import datetime
from kiteconnect import KiteConnect
from .portfolio import LivePortfolio
from Algorithms.base_strategy import BaseStrategy
from Common import Signal, SignalType
from DataStream_Engine import BuyInstant, SellInstant
import logging

logger = logging.getLogger(__name__)

class LiveTrader:
    
    def __init__(self, kite: KiteConnect, strategy: BaseStrategy):
        self.kite = kite
        self.strategy = strategy
        self.portfolio = LivePortfolio(kite)
        self.buy_action = BuyInstant(kite)
        self.sell_action = SellInstant(kite)
        self.current_prices: Dict[str, float] = {}
    
    def on_tick(self, tick):
        symbol = tick.get('tradingsymbol')
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
        
        try:
            order_id = self.buy_action.execute(signal.symbol, quantity)
            logger.info(f"Live buy order placed: {order_id} for {quantity} {signal.symbol}")
        except Exception as e:
            logger.error(f"Error placing buy order: {e}")
    
    def _execute_sell(self, signal: Signal):
        positions = self.portfolio.get_positions()
        
        if signal.symbol not in positions:
            logger.warning(f"No position to sell: {signal.symbol}")
            return
        
        pos = positions[signal.symbol]
        quantity = signal.quantity or pos.quantity
        
        try:
            order_id = self.sell_action.execute(signal.symbol, quantity)
            logger.info(f"Live sell order placed: {order_id} for {quantity} {signal.symbol}")
        except Exception as e:
            logger.error(f"Error placing sell order: {e}")
    
    def _calculate_quantity(self, symbol: str, price: float) -> int:
        margins = self.portfolio.get_margins()
        available = margins.get('equity', {}).get('available', {}).get('live_balance', 0)
        max_allocation = available * 0.1
        quantity = int(max_allocation / price)
        return max(1, quantity)
    
    def get_status(self) -> dict:
        positions = self.portfolio.get_positions()
        margins = self.portfolio.get_margins()
        
        return {
            'positions': len(positions),
            'margins': margins.get('equity', {}),
            'current_prices': self.current_prices
        }

