from typing import Dict, List, Optional
from datetime import datetime, time
from .portfolio import PaperPortfolio
from Algorithms.base_strategy import BaseStrategy
from Common import Order, Signal, SignalType, TransactionType, OrderType, OrderStatus
from DataStream_Engine import DataStream
import logging

logger = logging.getLogger(__name__)

class PaperTrader:
    
    def __init__(self, strategy: BaseStrategy, initial_capital: float = 100000, 
                 time_stop: str = '15:20', partial_exit_pct: float = 0.5):
        self.strategy = strategy
        self.portfolio = PaperPortfolio(initial_capital)
        self.current_prices: Dict[str, float] = {}
        self.current_atrs: Dict[str, float] = {}  # Track ATR for trailing stops
        self.time_stop = time_stop
        self.partial_exit_pct = partial_exit_pct
        
        # Parse time_stop
        hour, minute = map(int, time_stop.split(':'))
        self.time_stop_obj = time(hour, minute)
    
    def on_tick(self, tick):
        symbol = tick.get('instrument_token')
        price = tick.get('last_price', 0)
        
        if symbol and price:
            self.current_prices[symbol] = price
            self.portfolio.update_position_prices(symbol, price)
    
    def update_positions(self, current_time: datetime, market_data: Dict[str, any]):
        # Check time stop first
        if current_time.time() >= self.time_stop_obj:
            self._close_all_positions(current_time, "Time stop")
            return
        
        positions_to_close = []
        positions_to_partial_exit = []
        
        for symbol, pos in list(self.portfolio.positions.items()):
            # Update current price
            if symbol in self.current_prices:
                self.portfolio.update_position_prices(symbol, self.current_prices[symbol])
            
            # Get current ATR for trailing stop
            trail_atr_mult = getattr(self.strategy.params, 'trail_atr_mult', 2.0)
            current_atr = self.current_atrs.get(symbol, 0)
            
            # 1. Check stop loss
            if self.portfolio.check_stop_loss(symbol):
                positions_to_close.append((symbol, pos.quantity, "Stop loss"))
                continue
            
            # 2. Check partial exit trigger
            partial_qty = self.portfolio.check_partial_exit(symbol, self.partial_exit_pct)
            if partial_qty:
                positions_to_partial_exit.append((symbol, partial_qty, "Partial exit at +1R"))
            
            # 3. Check breakeven stop
            self.portfolio.check_breakeven_stop(symbol)
            
            # 4. Update trailing stop
            if current_atr > 0:
                self.portfolio.update_trailing_stop(symbol, trail_atr_mult, current_atr)
            
            # 5. Check target (full exit)
            if self.portfolio.check_target(symbol):
                positions_to_close.append((symbol, pos.quantity, "Target hit"))
                continue
        
        # Execute partial exits
        for symbol, quantity, reason in positions_to_partial_exit:
            self._exit_position(symbol, quantity, current_time, reason)
        
        # Execute full exits (use remaining quantity after partial exits)
        for symbol, quantity, reason in positions_to_close:
            if symbol in self.portfolio.positions:
                actual_quantity = self.portfolio.positions[symbol].quantity
                self._exit_position(symbol, actual_quantity, current_time, reason)
    
    def _close_all_positions(self, current_time: datetime, reason: str = "Market close"):
        for symbol, pos in list(self.portfolio.positions.items()):
            self._exit_position(symbol, pos.quantity, current_time, reason)
    
    def _exit_position(self, symbol: str, quantity: int, current_time: datetime, reason: str):
        if symbol not in self.portfolio.positions:
            return
        
        current_price = self.current_prices.get(symbol)
        if current_price is None:
            logger.warning(f"No current price for {symbol}, cannot exit")
            return
        
        order = Order(
            symbol=symbol,
            quantity=quantity,
            price=current_price,
            order_type=OrderType.MARKET,
            transaction_type=TransactionType.SELL,
            timestamp=current_time,
            status=OrderStatus.COMPLETE
        )
        
        if self.portfolio.execute_order(order, current_price):
            logger.info(f"Position exit: {quantity} {symbol} @ {current_price:.2f} - {reason}")
    
    def process_signals(self, signals: List[Signal]):
        for signal in signals:
            if hasattr(self, 'time_stop_obj'):
                current_time = signal.timestamp.time()
                if current_time >= self.time_stop_obj:
                    continue
            
            if signal.signal_type == SignalType.BUY:
                self._execute_buy(signal)
            elif signal.signal_type == SignalType.SELL:
                self._execute_sell(signal)
    
    def _execute_buy(self, signal: Signal):
        # Skip if already have position
        if signal.symbol in self.portfolio.positions:
            logger.debug(f"Already have position in {signal.symbol}, skipping buy signal")
            return
        
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
        
        if self.portfolio.execute_order(order, signal.price, signal=signal):
            logger.info(f"Paper buy: {quantity} {signal.symbol} @ {signal.price:.2f} | "
                       f"Stop: {signal.stop_loss:.2f if signal.stop_loss else 'N/A'} | "
                       f"Target: {signal.target:.2f if signal.target else 'N/A'}")
    
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
        
        if self.portfolio.execute_order(order, signal.price, signal=signal):
            logger.info(f"Paper sell: {quantity} {signal.symbol} @ {signal.price:.2f}")
    
    def _calculate_quantity(self, symbol: str, price: float) -> int:
        max_allocation = self.portfolio.cash * 0.1
        quantity = int(max_allocation / price)
        return max(1, quantity)
    
    def set_atr(self, symbol: str, atr: float):
        self.current_atrs[symbol] = atr
    
    def get_status(self) -> dict:
        total_value = self.portfolio.get_total_value(self.current_prices)
        return {
            'portfolio': self.portfolio.get_summary(),
            'total_value': total_value,
            'returns': (total_value - self.portfolio.initial_capital) / self.portfolio.initial_capital
        }

