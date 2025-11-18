from typing import Dict, List
import pandas as pd
from datetime import datetime
from .base_strategy import BaseStrategy
from Common import Signal, SignalType

class RSIStrategy(BaseStrategy):
    
    def __init__(self, params: dict = None):
        default_params = {
            'rsi_period': 14,
            'oversold': 30,
            'overbought': 70,
            'min_confidence': 0.7
        }
        if params:
            default_params.update(params)
        super().__init__(default_params)
    
    def generate_signals(self, data: Dict[str, pd.DataFrame], 
                        current_date: datetime) -> List[Signal]:
        signals = []
        
        rsi_period = self.params['rsi_period']
        oversold = self.params['oversold']
        overbought = self.params['overbought']
        
        for symbol, df in data.items():
            if len(df) < rsi_period + 1:
                continue
            
            rsi = self.static_ind.rsi(df['close'], rsi_period)
            current_rsi = self.get_latest_value(rsi)
            current_price = df['close'].iloc[-1]
            
            if current_rsi < oversold and len(rsi) >= 2 and rsi.iloc[-2] >= oversold:
                signals.append(Signal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    price=current_price,
                    timestamp=current_date,
                    confidence=0.8,
                    reason=f"RSI oversold: {current_rsi:.2f}"
                ))
            
            elif current_rsi > overbought and len(rsi) >= 2 and rsi.iloc[-2] <= overbought:
                signals.append(Signal(
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    price=current_price,
                    timestamp=current_date,
                    confidence=0.8,
                    reason=f"RSI overbought: {current_rsi:.2f}"
                ))
        
        return signals

