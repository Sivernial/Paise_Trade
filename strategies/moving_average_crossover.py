"""
Moving Average Crossover Strategy

Simple moving average crossover strategy:
- Buy when fast MA crosses above slow MA
- Sell when fast MA crosses below slow MA
"""

import pandas as pd
from typing import Dict, List, Any
from datetime import datetime

from strategies.base_strategy import BaseStrategy
from data_structures.strategy_dataclass import Signal
from data_structures.common import SignalType


class MovingAverageCrossoverStrategy(BaseStrategy):
    """
    Simple moving average crossover strategy
    Buy when fast MA crosses above slow MA, sell when it crosses below
    """
    
    def __init__(self, kite=None, params: Dict[str, Any] = None):
        default_params = {
            'fast_period': 10,
            'slow_period': 20,
            'min_confidence': 0.7
        }
        default_params.update(params or {})
        super().__init__(kite, default_params)
        
        self.fast_period = self.params['fast_period']
        self.slow_period = self.params['slow_period']
    
    def generate_signals(self, data: Dict[str, pd.DataFrame], current_date: datetime) -> List[Signal]:
        signals = []
        
        for symbol, df in data.items():
            if len(df) < self.slow_period:
                continue
            
            # Calculate moving averages
            fast_ma = self.ta.sma(df['close'], self.fast_period)
            slow_ma = self.ta.sma(df['close'], self.slow_period)
            
            current_price = df['close'].iloc[-1]
            
            # Check for crossovers
            if self.is_bullish_crossover(fast_ma, slow_ma):
                signal = Signal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    confidence=0.75,
                    price=current_price,
                    timestamp=current_date,
                    reason=f"Bullish MA crossover: {self.fast_period}-day MA crossed above {self.slow_period}-day MA"
                )
                signals.append(signal)
                
            elif self.is_bearish_crossover(fast_ma, slow_ma):
                signal = Signal(
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    confidence=0.75,
                    price=current_price,
                    timestamp=current_date,
                    reason=f"Bearish MA crossover: {self.fast_period}-day MA crossed below {self.slow_period}-day MA"
                )
                signals.append(signal)
        
        return signals