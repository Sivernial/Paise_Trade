"""
Multi-Indicator Strategy

Advanced strategy combining multiple technical indicators:
- Moving averages (MA filter)
- RSI (momentum filter)
- MACD (trend filter)
- Scoring system for signal generation
- High confidence only when multiple indicators align
"""

import pandas as pd
from typing import Dict, List, Any
from datetime import datetime

from strategies.base_strategy import BaseStrategy
from data_structures.strategy_dataclass import Signal
from data_structures.common import SignalType


class MultiIndicatorStrategy(BaseStrategy):
    """
    Advanced strategy combining multiple technical indicators
    """
    
    def __init__(self, kite=None, params: Dict[str, Any] = None):
        default_params = {
            'use_ma_filter': True,
            'use_rsi_filter': True,
            'use_macd_filter': True,
            'min_confidence': 0.8
        }
        default_params.update(params or {})
        super().__init__(kite, default_params)
    
    def generate_signals(self, data: Dict[str, pd.DataFrame], current_date: datetime) -> List[Signal]:
        signals = []
        
        for symbol, df in data.items():
            if len(df) < 50:  # Need enough data for all indicators
                continue
            
            # Calculate all indicators
            indicators = self.calculate_indicators(df, symbol)
            current_price = df['close'].iloc[-1]
            
            # Multi-indicator analysis
            buy_score = 0
            sell_score = 0
            reasons = []
            
            # Moving average filter
            if self.params['use_ma_filter'] and 'sma_20' in indicators and 'sma_50' in indicators:
                sma20 = indicators['sma_20']
                sma50 = indicators['sma_50']
                
                if isinstance(sma20, pd.Series):
                    sma20 = sma20.iloc[-1]
                if isinstance(sma50, pd.Series):
                    sma50 = sma50.iloc[-1]
                
                if sma20 > sma50:
                    buy_score += 1
                    reasons.append("MA bullish trend")
                elif sma20 < sma50:
                    sell_score += 1
                    reasons.append("MA bearish trend")
            
            # RSI filter
            if self.params['use_rsi_filter'] and 'rsi' in indicators:
                rsi = indicators['rsi']
                if isinstance(rsi, pd.Series):
                    rsi = rsi.iloc[-1]
                
                if rsi < 40:
                    buy_score += 1
                    reasons.append(f"RSI oversold ({rsi:.1f})")
                elif rsi > 60:
                    sell_score += 1
                    reasons.append(f"RSI overbought ({rsi:.1f})")
            
            # MACD filter
            if (self.params['use_macd_filter'] and 
                'macd' in indicators and 'macd_signal' in indicators):
                
                macd = indicators['macd']
                macd_signal = indicators['macd_signal']
                
                if isinstance(macd, pd.Series):
                    macd = macd.iloc[-1]
                if isinstance(macd_signal, pd.Series):
                    macd_signal = macd_signal.iloc[-1]
                
                if macd > macd_signal:
                    buy_score += 1
                    reasons.append("MACD bullish")
                elif macd < macd_signal:
                    sell_score += 1
                    reasons.append("MACD bearish")
            
            # Generate signals based on scores
            total_indicators = sum([
                self.params['use_ma_filter'],
                self.params['use_rsi_filter'],
                self.params['use_macd_filter']
            ])
            
            if buy_score >= 2:
                confidence = min(0.95, 0.5 + (buy_score / total_indicators) * 0.4)
                signal = Signal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    confidence=confidence,
                    price=current_price,
                    timestamp=current_date,
                    reason=f"Multi-indicator BUY ({buy_score}/{total_indicators}): " + ", ".join(reasons),
                    indicators=indicators
                )
                signals.append(signal)
            
            elif sell_score >= 2:
                confidence = min(0.95, 0.5 + (sell_score / total_indicators) * 0.4)
                signal = Signal(
                    symbol=symbol,
                    signal_type=SignalType.SELL,
                    confidence=confidence,
                    price=current_price,
                    timestamp=current_date,
                    reason=f"Multi-indicator SELL ({sell_score}/{total_indicators}): " + ", ".join(reasons),
                    indicators=indicators
                )
                signals.append(signal)
        
        return signals