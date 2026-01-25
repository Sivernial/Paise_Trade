from typing import Dict, List, Optional
from datetime import datetime, time
from .portfolio import PaperPortfolio
from Algorithms.base_strategy import BaseStrategy
from Common import Order, Signal, SignalType, TransactionType, OrderType, OrderStatus
from DataStream_Engine.aggregator import TickAggregator
import logging

logger = logging.getLogger(__name__)

class PaperTrader:
    
    def __init__(self, strategy: BaseStrategy, initial_capital: float = 100000, trade_repo = None):
        self.strategy = strategy
        self.portfolio = PaperPortfolio(initial_capital)
        self.trade_repo = trade_repo
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
            elif signal.signal_type == SignalType.EXIT:
                self._execute_exit(signal)
    
    def check_security(self):
        """
        High-frequency check for SL/TP on every tick.
        """
        positions = self.portfolio.get_positions()
        for symbol in list(positions.keys()):
            price = self.current_prices.get(symbol)
            if not price: continue
            
            # Update internal prices for trailing/pnl calc
            self.portfolio.update_position_prices(symbol, price)
            
            # Check Stop Loss
            if self.portfolio.check_stop_loss(symbol):
                reason = f"SECURITY EXIT: Stop Loss hit at {price:.2f}"
                logger.warning(reason)
                self._execute_exit(Signal(symbol, SignalType.EXIT, price, datetime.now(), 0, reason))
                
            # Check Profit Target
            elif self.portfolio.check_target(symbol):
                reason = f"SECURITY EXIT: Profit Target hit at {price:.2f}"
                logger.info(reason)
                self._execute_exit(Signal(symbol, SignalType.EXIT, price, datetime.now(), 0, reason))
    
    def _execute_exit(self, signal: Signal):
        """Flatten any existing position for the symbol."""
        positions = self.portfolio.get_positions()
        if signal.symbol not in positions:
            # logger.debug(f"No position to exit for {signal.symbol}")
            return
            
        pos = positions[signal.symbol]
        trans_type = TransactionType.SELL if pos.quantity > 0 else TransactionType.BUY
        
        logger.info(f"Generated EXIT order for {signal.symbol}: Closing {pos.quantity}")
        
        order = Order(
            symbol=signal.symbol,
            quantity=abs(pos.quantity),
            price=signal.price,
            order_type=OrderType.MARKET,
            transaction_type=trans_type,
            timestamp=datetime.now(),
            status=OrderStatus.COMPLETE
        )
        
        res = self.portfolio.execute_order(order, signal.price, signal=signal)
        if res:
            logger.info(f"Successfully EXITED position for {signal.symbol}")
            if isinstance(res, dict) and self.trade_repo:
                self.trade_repo.save_trade(res)
    
    def _execute_buy(self, signal: Signal):
        # Calculate quantity
        price = signal.price
        quantity = signal.quantity 
        
        # Check if we're covering a short position
        positions = self.portfolio.get_positions()
        pos = positions.get(signal.symbol)
        
        if pos and pos.quantity < 0 and quantity <= 0:
            # Covering a short - use full position quantity
            quantity = abs(pos.quantity)
            logger.info(f"Covering SHORT position: {signal.symbol} Qty: {quantity}")
        elif quantity <= 0:
            # New BUY or no position - use default calculation
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
        
        res = self.portfolio.execute_order(order, price, signal=signal)
        if res:
            logger.info(f"Executed BUY {quantity} {signal.symbol}")
            if isinstance(res, dict) and self.trade_repo:
                self.trade_repo.save_trade(res)

    def _execute_sell(self, signal: Signal):
        price = signal.price
        quantity = signal.quantity
        
        # Check if we're covering a long position
        positions = self.portfolio.get_positions()
        pos = positions.get(signal.symbol)
        
        if pos and pos.quantity > 0 and quantity <= 0:
            # Covering a long - use full position quantity
            quantity = abs(pos.quantity)
            logger.info(f"Covering LONG position: {signal.symbol} Qty: {quantity}")
        elif quantity <= 0:
            # New SELL (short) or no position - use default calculation
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
        
        res = self.portfolio.execute_order(order, price, signal=signal)
        if res:
            logger.info(f"Executed SELL {quantity} {signal.symbol}")
            if isinstance(res, dict) and self.trade_repo:
                self.trade_repo.save_trade(res)

    def _calculate_default_quantity(self, price: float) -> int:
        # Respect the strategy's defined capital cap if present
        max_cap = self.strategy.params.get('max_capital')
        base_capital = min(self.portfolio.cash, max_cap) if max_cap else self.portfolio.cash
        
        # Default 10% allocation of the base capital
        alloc = base_capital * 0.1
        return max(1, int(alloc / price))

    def get_status(self) -> dict:
        total_value = self.portfolio.get_total_value(self.current_prices)
        return {
            'portfolio': self.portfolio.get_summary(),
            'total_value': total_value,
            'returns': (total_value - self.portfolio.initial_capital) / self.portfolio.initial_capital
        }
