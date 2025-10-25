"""
RSI Mean Reversion Strategy

RSI-based mean reversion strategy:
- Buy when RSI is oversold (typically < 30)
- Sell when RSI is overbought (typically > 70)
- Confidence varies based on how extreme the RSI reading is
"""

import pandas as pd
from typing import Dict, List, Any
from datetime import datetime

from strategies.base_strategy import BaseStrategy
from data_structures.strategy_dataclass import Signal
from data_structures.common import SignalType


class RSIMeanReversionStrategy(BaseStrategy):
    """
    RSI-based mean reversion strategy
    Buy when RSI is oversold, sell when overbought
    """
    
    def __init__(self, kite=None, params: Dict[str, Any] = None):
        default_params = {
            'rsi_period': 14,
            'oversold_threshold': 30,
            'overbought_threshold': 70,
            'min_confidence': 0.6
        }
        default_params.update(params or {})
        super().__init__(kite, default_params)
        
        self.rsi_period = self.params['rsi_period']
        self.oversold_threshold = self.params['oversold_threshold']
        self.overbought_threshold = self.params['overbought_threshold']
    
    def generate_signals(self, data: Dict[str, pd.DataFrame], current_date: datetime) -> List[Signal]:
        signals = []
        
        for symbol, df in data.items():
            if len(df) < self.rsi_period + 1:
                continue
            
            # Calculate RSI
            rsi = self.ta.rsi(df['close'], self.rsi_period)
            current_rsi = rsi.iloc[-1]
            current_price = df['close'].iloc[-1]
            
            # Check for oversold condition (buy signal)
            if self.is_oversold(current_rsi, self.oversold_threshold):
                confidence = min(0.9, (self.oversold_threshold - current_rsi) / self.oversold_threshold + 0.5)
                signal = Signal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    confidence=confidence,
                    price=current_price,
                    timestamp=current_date,
                    reason=f"RSI oversold: {current_rsi:.1f} < {self.oversold_threshold}",
                    indicators={'rsi': current_rsi}
                )
                signals.append(signal)
            
            # Check for overbought condition (sell signal)
            elif self.is_overbought(current_rsi, self.overbought_threshold):
                confidence = min(0.9, (current_rsi - self.overbought_threshold) / (100 - self.overbought_threshold) + 0.5)
                signal = Signal(
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    confidence=confidence,
                    price=current_price,
                    timestamp=current_date,
                    reason=f"RSI overbought: {current_rsi:.1f} > {self.overbought_threshold}",
                    indicators={'rsi': current_rsi}
                )
                signals.append(signal)
        
        return signals