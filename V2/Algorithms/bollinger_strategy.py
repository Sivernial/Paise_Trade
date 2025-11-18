from typing import Dict, List
import pandas as pd
from datetime import datetime
from .base_strategy import BaseStrategy
from Common import Signal, SignalType

class BollingerStrategy(BaseStrategy):
    
    def __init__(self, params: dict = None):
        default_params = {
            'bb_period': 20,
            'bb_std': 2,
            'min_confidence': 0.7
        }
        if params:
            default_params.update(params)
        super().__init__(default_params)
    
    def generate_signals(self, data: Dict[str, pd.DataFrame], 
                        current_date: datetime) -> List[Signal]:
        signals = []
        
        bb_period = self.params['bb_period']
        bb_std = self.params['bb_std']
        
        for symbol, df in data.items():
            if len(df) < bb_period:
                continue
            
            upper, middle, lower = self.static_ind.bollinger_bands(
                df['close'], bb_period, bb_std
            )
            
            current_price = df['close'].iloc[-1]
            current_upper = self.get_latest_value(upper)
            current_lower = self.get_latest_value(lower)
            
            if len(df) >= 2:
                prev_price = df['close'].iloc[-2]
                
                if prev_price > current_lower and current_price <= current_lower:
                    signals.append(Signal(
                        symbol=symbol,
                        signal_type=SignalType.BUY,
                        price=current_price,
                        timestamp=current_date,
                        confidence=0.75,
                        reason=f"Price touched lower BB: {current_price:.2f}"
                    ))
                
                elif prev_price < current_upper and current_price >= current_upper:
                    signals.append(Signal(
                        symbol=symbol,
                        signal_type=SignalType.SELL,
                        price=current_price,
                        timestamp=current_date,
                        confidence=0.75,
                        reason=f"Price touched upper BB: {current_price:.2f}"
                    ))
        
        return signals

