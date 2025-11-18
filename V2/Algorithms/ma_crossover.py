from typing import Dict, List
import pandas as pd
from datetime import datetime
from .base_strategy import BaseStrategy
from Common import Signal, SignalType

class MACrossoverStrategy(BaseStrategy):
    
    def __init__(self, params: dict = None):
        default_params = {
            'fast_period': 10,
            'slow_period': 20,
            'min_confidence': 0.7
        }
        if params:
            default_params.update(params)
        super().__init__(default_params)
    
    def generate_signals(self, data: Dict[str, pd.DataFrame], 
                        current_date: datetime) -> List[Signal]:
        signals = []
        
        fast_period = self.params['fast_period']
        slow_period = self.params['slow_period']
        
        for symbol, df in data.items():
            if len(df) < slow_period:
                continue
            
            fast_ma = self.static_ind.sma(df['close'], fast_period)
            slow_ma = self.static_ind.sma(df['close'], slow_period)
            
            current_price = df['close'].iloc[-1]
            
            if self.is_bullish_crossover(fast_ma, slow_ma):
                signals.append(Signal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    price=current_price,
                    timestamp=current_date,
                    confidence=0.75,
                    reason=f"MA crossover: {fast_period} crossed above {slow_period}"
                ))
            
            elif self.is_bearish_crossover(fast_ma, slow_ma):
                signals.append(Signal(
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    price=current_price,
                    timestamp=current_date,
                    confidence=0.75,
                    reason=f"MA crossover: {fast_period} crossed below {slow_period}"
                ))
        
        return signals

