"""
Bollinger Band Strategy

Enhanced Bollinger Band strategy based on Investopedia best practices:

Features:
- Multiple trading modes: reversal, breakout, squeeze breakout
- Volume confirmation for signals
- Squeeze detection for anticipating major moves
- %B and bandwidth analysis
- Risk management with stop losses
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime

from strategies.base_strategy import BaseStrategy
from data_structures.strategy_dataclass import Signal
from data_structures.common import SignalType


class BollingerBandStrategy(BaseStrategy):
    """
    Enhanced Bollinger Band strategy based on Investopedia best practices
    
    Features:
    - Multiple trading modes: reversal, breakout, squeeze breakout
    - Volume confirmation for signals
    - Squeeze detection for anticipating major moves
    - %B and bandwidth analysis
    - Risk management with stop losses
    """
    
    def __init__(self, kite=None, params: Dict[str, Any] = None):
        default_params = {
            'bb_period': 15,  # Shorter period for more responsive signals
            'bb_std': 1.5,    # Lower std dev for more frequent signals
            'strategy_type': 'adaptive',  # 'reversal', 'breakout', 'squeeze', 'adaptive'
            'min_confidence': 0.65,
            'volume_confirmation': False,  # Disable by default to get more signals
            'squeeze_lookback': 10,
            'risk_reward_ratio': 2.0,
            'stop_loss_pct': 0.02  # 2% stop loss
        }
        default_params.update(params or {})
        super().__init__(kite, default_params)
        
        self.bb_period = self.params['bb_period']
        self.bb_std = self.params['bb_std']
        self.strategy_type = self.params['strategy_type']
        self.volume_confirmation = self.params['volume_confirmation']
        
    def generate_signals(self, data: Dict[str, pd.DataFrame], current_date: datetime) -> List[Signal]:
        signals = []
        
        for symbol, df in data.items():
            if len(df) < self.bb_period + 5:  # Need BB period + small buffer
                continue
            
            try:
                # Calculate all Bollinger Band indicators
                bb_upper, bb_middle, bb_lower = self.ta.bollinger_bands(
                    df['close'], self.bb_period, self.bb_std
                )
                
                bb_width = self.ta.bollinger_band_width(df['close'], self.bb_period, self.bb_std)
                bb_squeeze = self.ta.bollinger_squeeze(
                    df['close'], self.bb_period, self.bb_std, self.params['squeeze_lookback']
                )
                percent_b = self.ta.bollinger_percent_b(df['close'], self.bb_period, self.bb_std)
                
                current_price = df['close'].iloc[-1]
                current_upper = bb_upper.iloc[-1]
                current_lower = bb_lower.iloc[-1]
                current_middle = bb_middle.iloc[-1]
                current_width = bb_width.iloc[-1]
                current_squeeze = bb_squeeze.iloc[-1]
                current_percent_b = percent_b.iloc[-1]
                
                # Volume analysis if available
                volume_spike = False
                if 'volume' in df.columns and self.volume_confirmation:
                    volume_ma = df['volume'].rolling(window=20).mean()
                    current_volume = df['volume'].iloc[-1]
                    avg_volume = volume_ma.iloc[-1]
                    volume_spike = current_volume > (avg_volume * 1.5)  # 50% above average
                
                # Strategy selection
                if self.strategy_type == 'adaptive':
                    # Choose strategy based on current market conditions
                    if current_squeeze:
                        strategy_mode = 'squeeze'
                    elif current_width > bb_width.rolling(20).mean().iloc[-1]:
                        strategy_mode = 'breakout'  # High volatility
                    else:
                        strategy_mode = 'reversal'  # Normal conditions
                else:
                    # Default to reversal if strategy_type is None or invalid
                    strategy_mode = self.strategy_type or 'reversal'
                
                # Generate signals based on strategy mode
                signal = self._generate_bb_signal(
                    symbol, df, current_date, current_price,
                    current_upper, current_lower, current_middle,
                    current_percent_b, current_squeeze, volume_spike,
                    strategy_mode
                )
                
                if signal:
                    signals.append(signal)
                    
            except Exception as e:
                print(f"⚠️ Error analyzing {symbol}: {e}")
                continue
        
        return signals
    
    def _generate_bb_signal(self, symbol: str, df: pd.DataFrame, current_date: datetime,
                           current_price: float, upper: float, lower: float, middle: float,
                           percent_b: float, is_squeeze: bool, volume_spike: bool,
                           strategy_mode: str) -> Optional[Signal]:
        """Generate signal based on Bollinger Band analysis"""
        
        confidence = 0.5
        reason_parts = []
        signal_type = None
        
        if strategy_mode == 'squeeze':
            # Squeeze breakout strategy
            if is_squeeze and volume_spike:
                # Wait for breakout after squeeze
                if current_price > upper:
                    signal_type = SignalType.BUY
                    confidence = 0.85
                    reason_parts.append("Bullish breakout after BB squeeze")
                elif current_price < lower:
                    signal_type = SignalType.SELL
                    confidence = 0.85
                    reason_parts.append("Bearish breakdown after BB squeeze")
        
        elif strategy_mode == 'breakout':
            # Breakout strategy with volume confirmation
            if current_price > upper and (not self.volume_confirmation or volume_spike):
                signal_type = SignalType.BUY
                confidence = 0.75 + (0.1 if volume_spike else 0)
                reason_parts.append("Bullish breakout above upper BB")
                
            elif current_price < lower and (not self.volume_confirmation or volume_spike):
                signal_type = SignalType.SELL
                confidence = 0.75 + (0.1 if volume_spike else 0)
                reason_parts.append("Bearish breakdown below lower BB")
        
        elif strategy_mode == 'reversal':
            # Mean reversion strategy
            if percent_b <= 0:  # Below lower band
                signal_type = SignalType.BUY
                confidence = 0.7 + min(0.2, abs(percent_b) * 0.5)  # Higher confidence for deeper oversold
                reason_parts.append(f"Oversold at lower BB (%B: {percent_b:.2f})")
                
            elif percent_b >= 1:  # Above upper band
                signal_type = SignalType.SELL
                confidence = 0.7 + min(0.2, (percent_b - 1) * 0.5)  # Higher confidence for deeper overbought
                reason_parts.append(f"Overbought at upper BB (%B: {percent_b:.2f})")
        
        # Additional signal enhancement
        if signal_type:
            # Add volume confirmation to reason
            if volume_spike:
                reason_parts.append("with volume spike")
                confidence = min(0.95, confidence + 0.1)
            
            # Add squeeze context
            if is_squeeze:
                reason_parts.append("during BB squeeze")
                confidence = min(0.95, confidence + 0.05)
            
            # Calculate stop loss and take profit
            if signal_type == SignalType.BUY:
                stop_loss = current_price * (1 - self.params['stop_loss_pct'])
                take_profit = current_price * (1 + self.params['stop_loss_pct'] * self.params['risk_reward_ratio'])
            else:
                stop_loss = current_price * (1 + self.params['stop_loss_pct'])
                take_profit = current_price * (1 - self.params['stop_loss_pct'] * self.params['risk_reward_ratio'])
            
            return Signal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                price=current_price,
                timestamp=current_date,
                reason=f"BB {strategy_mode.title()}: " + ", ".join(reason_parts),
                indicators={
                    'bb_upper': upper,
                    'bb_lower': lower,
                    'bb_middle': middle,
                    'percent_b': percent_b,
                    'is_squeeze': is_squeeze,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit
                }
            )
        
        return None