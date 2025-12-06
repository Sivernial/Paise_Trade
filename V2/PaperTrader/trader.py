from typing import Dict, List, Optional
from datetime import datetime, time
from .portfolio import PaperPortfolio
from Algorithms.base_strategy import BaseStrategy
from Common import Order, Signal, SignalType, TransactionType, OrderType, OrderStatus
from DataStream_Engine.aggregator import TickAggregator
import logging

logger = logging.getLogger(__name__)

class PaperTrader:
    
    def __init__(self, strategy: BaseStrategy, initial_capital: float = 100000):
        self.strategy = strategy
        self.portfolio = PaperPortfolio(initial_capital)
        self.current_prices: Dict[str, float] = {}
        
        # Buffer for completed candles to pass to strategy
        self.candle_buffer: Dict[str, List] = {} 
    
    def on_tick(self, ticks):
        for tick in ticks:
            token = tick.get('instrument_token')
            price = tick.get('last_price')
            if token and price:
                # Map token to symbol if possible, or assume external mapping.
                # Ideally, we key by Instrument Token, but Strategy uses Symbols.
                # The Runner should handle mapping. 
                # For now, let's assume 'ticks' passed here are enriched or we rely on Aggregator for bars.
                pass

    def on_candle_closed(self, symbol: str, candle):
        """
        Callback from Aggregator when a candle closes.
        """
        logger.info(f"Candle closed for {symbol}: {candle.iloc[-1]['close']}")
        
        # Update Strategy
        # Strategy usually needs a DataFrame of history. 
        # In live, we append this candle to a running history.
        # For simplicity in this version, we assume strategy.generate_signals 
        # can take a single row or we manage state externally.
        # But `PairTradingStrategy` expects full series for Z-score.
        # So we MUST maintain history.
        
        # We delegate this to a 'DataHandler' or simple dictionary here.
        # Note: Ideally this history management belongs in a common Data layer.
        pass

    def process_signals(self, signals: List[Signal]):
        for signal in signals:
            if signal.signal_type == SignalType.BUY:
                self._execute_buy(signal)
            elif signal.signal_type == SignalType.SELL:
                self._execute_sell(signal)
    
    def _execute_buy(self, signal: Signal):
        # Calculate quantity
        price = signal.price
        quantity = signal.quantity 
        
        if quantity <= 0:
            # Fallback or error
            quantity = self._calculate_default_quantity(price)
            
        logger.info(f"Generated BUY order: {signal.symbol} Qty: {quantity} @ {price}")
        
        order = Order(
            symbol=signal.symbol,
            quantity=quantity,
            price=price,
            order_type=OrderType.MARKET,
            transaction_type=TransactionType.BUY,
            timestamp=datetime.now(),
            status=OrderStatus.COMPLETE
        )
        
        if self.portfolio.execute_order(order, price, signal=signal):
            logger.info(f"Executed BUY {quantity} {signal.symbol}")

    def _execute_sell(self, signal: Signal):
        price = signal.price
        quantity = signal.quantity
        
        if quantity <= 0:
            quantity = self._calculate_default_quantity(price)
            
        logger.info(f"Generated SELL order: {signal.symbol} Qty: {quantity} @ {price}")
            
        order = Order(
            symbol=signal.symbol,
            quantity=quantity,
            price=price,
            order_type=OrderType.MARKET,
            transaction_type=TransactionType.SELL, # Supports Short Selling
            timestamp=datetime.now(),
            status=OrderStatus.COMPLETE
        )
        
        if self.portfolio.execute_order(order, price, signal=signal):
            logger.info(f"Executed SELL {quantity} {signal.symbol}")

    def _calculate_default_quantity(self, price: float) -> int:
        # Default 10% allocation
        alloc = self.portfolio.cash * 0.1
        return max(1, int(alloc / price))

    def get_status(self) -> dict:
        total_value = self.portfolio.get_total_value(self.current_prices)
        return {
            'portfolio': self.portfolio.get_summary(),
            'total_value': total_value,
            'returns': (total_value - self.portfolio.initial_capital) / self.portfolio.initial_capital
        }
