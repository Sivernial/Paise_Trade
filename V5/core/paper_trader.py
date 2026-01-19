"""
Paper trading engine for V5.
Processes signals and manages portfolio without real money.
"""
import logging
from typing import List, Dict
from datetime import datetime
from .portfolio import Portfolio
from ..common.models import Signal, SignalType, TransactionType

logger = logging.getLogger(__name__)

class PaperTrader:
    """Paper trading engine that simulates real trading."""
    
    def __init__(self, initial_capital: float = 100000):
        self.portfolio = Portfolio(initial_capital)
        self.current_prices: Dict[str, float] = {}
        
    def process_signals(self, signals: List[Signal]):
        """Process a list of trading signals."""
        for signal in signals:
            self.process_signal(signal)
    
    def process_signal(self, signal: Signal):
        """Process a single trading signal."""
        symbol = signal.symbol
        
        if signal.signal_type == SignalType.BUY:
            # Open long position
            if symbol not in self.portfolio.positions:
                self.portfolio.add_position(
                    symbol, signal.quantity, signal.price, signal.timestamp
                )
                logger.info(f"BUY {symbol} x {signal.quantity} @ {signal.price} | {signal.reason}")
            else:
                logger.debug(f"Already in position for {symbol}, ignoring BUY signal")
        
        elif signal.signal_type == SignalType.SELL:
            # Open short position
            if symbol not in self.portfolio.positions:
                self.portfolio.add_position(
                    symbol, -signal.quantity, signal.price, signal.timestamp
                )
                logger.info(f"SELL {symbol} x {signal.quantity} @ {signal.price} | {signal.reason}")
            else:
                logger.debug(f"Already in position for {symbol}, ignoring SELL signal")
        
        elif signal.signal_type == SignalType.EXIT:
            # Close existing position
            if symbol in self.portfolio.positions:
                pnl = self.portfolio.close_position(symbol, signal.price, signal.timestamp)
                logger.info(f"EXIT {symbol} @ {signal.price} | PnL: {pnl:.2f} | {signal.reason}")
            else:
                logger.debug(f"No position to exit for {symbol}")
    
    def get_status(self) -> dict:
        """Get current portfolio status."""
        return {
            'cash': self.portfolio.cash,
            'total_value': self.portfolio.get_total_value(),
            'pnl': self.portfolio.get_pnl(),
            'positions': len(self.portfolio.positions),
            'portfolio': {
                'positions': self.portfolio.get_positions(),
                'trades': len(self.portfolio.trade_history)
            }
        }
