"""
Enhanced Strategy Framework for Algorithmic Trading
Provides base classes and utilities for building trading strategies
"""

import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

# Import dataclasses from data_structures
from data_structures.strategy_dataclass import Signal
from data_structures.common import SignalType, OrderType

from .technical_analysis import TechnicalIndicators, PatternRecognition, TrendAnalysis
from .backtesting import BacktestEngine

class BaseStrategy(ABC):
    """
    Enhanced base class for trading strategies
    
    Features:
    - Technical indicator integration
    - Signal generation framework
    - Risk management hooks
    - Performance tracking
    - Backtesting compatibility
    """
    
    def __init__(self, kite=None, params: Dict[str, Any] = None):
        self.kite = kite
        self.params = params or {}
        
        # Strategy state
        self.positions: Dict[str, int] = {}
        self.signals: List[Signal] = []
        self.indicators_cache: Dict[str, Dict] = {}
        
        # Performance tracking
        self.total_signals = 0
        self.profitable_signals = 0
        
        # Technical indicators instance
        self.ta = TechnicalIndicators()
        self.patterns = PatternRecognition()
        self.trend = TrendAnalysis()
        
        # Strategy parameters
        self.lookback_period = self.params.get('lookback_period', 50)
        self.min_confidence = self.params.get('min_confidence', 0.6)
        self.max_position_size = self.params.get('max_position_size', 1000)
        
    @abstractmethod
    def generate_signals(self, data: Dict[str, pd.DataFrame], current_date: datetime) -> List[Signal]:
        """
        Generate trading signals based on market data
        
        Args:
            data: Dictionary mapping symbols to OHLCV DataFrames
            current_date: Current simulation/trading date
            
        Returns:
            List of trading signals
        """
        pass
    
    def on_tick(self, tick):
        """Legacy method for real-time data compatibility"""
        # Convert tick to DataFrame format for consistency
        symbol = tick.get('instrument_token', 'UNKNOWN')
        current_data = {
            symbol: pd.DataFrame([{
                'close': tick.get('last_price', 0),
                'volume': tick.get('volume', 0),
                'timestamp': datetime.now()
            }])
        }
        
        signals = self.generate_signals(current_data, datetime.now())
        self.process_signals(signals)
    
    def process_signals(self, signals: List[Signal]):
        """Process generated signals"""
        for signal in signals:
            if signal.confidence >= self.min_confidence:
                self.execute_signal(signal)
                self.signals.append(signal)
                self.total_signals += 1
    
    def execute_signal(self, signal: Signal):
        """Execute a trading signal (override for live trading)"""
        print(f"🔔 {signal.signal_type.value} signal for {signal.symbol} "
              f"at ${signal.price:.2f} (confidence: {signal.confidence:.2%})")
        print(f"   Reason: {signal.reason}")
    
    def calculate_indicators(self, data: pd.DataFrame, symbol: str) -> Dict[str, pd.Series]:
        """Calculate technical indicators for a symbol"""
        if data.empty:
            return {}
        
        indicators = {}
        
        try:
            # Moving averages
            indicators['sma_20'] = self.ta.sma(data['close'], 20)
            indicators['sma_50'] = self.ta.sma(data['close'], 50)
            indicators['ema_12'] = self.ta.ema(data['close'], 12)
            indicators['ema_26'] = self.ta.ema(data['close'], 26)
            
            # Momentum indicators
            indicators['rsi'] = self.ta.rsi(data['close'], 14)
            indicators['momentum'] = self.ta.momentum(data['close'], 10)
            
            # MACD
            macd, signal_line, histogram = self.ta.macd(data['close'])
            indicators['macd'] = macd
            indicators['macd_signal'] = signal_line
            indicators['macd_histogram'] = histogram
            
            # Bollinger Bands
            if len(data) >= 20:
                bb_upper, bb_middle, bb_lower = self.ta.bollinger_bands(data['close'])
                indicators['bb_upper'] = bb_upper
                indicators['bb_middle'] = bb_middle
                indicators['bb_lower'] = bb_lower
            
            # Volume indicators
            if 'volume' in data.columns:
                indicators['volume_sma'] = self.ta.sma(data['volume'], 20)
            
            # Volatility
            if len(data) >= 14:
                indicators['atr'] = self.ta.atr(data['high'], data['low'], data['close'])
            
            # Cache indicators
            self.indicators_cache[symbol] = {k: v.iloc[-1] if len(v) > 0 else 0 for k, v in indicators.items()}
            
        except Exception as e:
            print(f"⚠️ Error calculating indicators for {symbol}: {e}")
        
        return indicators
    
    def get_trend_direction(self, data: pd.DataFrame) -> int:
        """Get trend direction: 1 (up), -1 (down), 0 (sideways)"""
        if len(data) < 20:
            return 0
        
        sma_short = self.ta.sma(data['close'], 10).iloc[-1]
        sma_long = self.ta.sma(data['close'], 20).iloc[-1]
        
        if sma_short > sma_long:
            return 1
        elif sma_short < sma_long:
            return -1
        else:
            return 0
    
    def is_oversold(self, rsi: float, threshold: float = 30) -> bool:
        """Check if RSI indicates oversold condition"""
        return rsi < threshold
    
    def is_overbought(self, rsi: float, threshold: float = 70) -> bool:
        """Check if RSI indicates overbought condition"""
        return rsi > threshold
    
    def is_bullish_crossover(self, fast_ma: pd.Series, slow_ma: pd.Series) -> bool:
        """Check for bullish moving average crossover"""
        if len(fast_ma) < 2 or len(slow_ma) < 2:
            return False
        
        return (fast_ma.iloc[-1] > slow_ma.iloc[-1] and 
                fast_ma.iloc[-2] <= slow_ma.iloc[-2])
    
    def is_bearish_crossover(self, fast_ma: pd.Series, slow_ma: pd.Series) -> bool:
        """Check for bearish moving average crossover"""
        if len(fast_ma) < 2 or len(slow_ma) < 2:
            return False
        
        return (fast_ma.iloc[-1] < slow_ma.iloc[-1] and 
                fast_ma.iloc[-2] >= slow_ma.iloc[-2])
    
    def calculate_position_size(self, symbol: str, price: float, risk_per_trade: float = 0.02) -> int:
        """Calculate position size based on risk management"""
        # Simplified position sizing - can be enhanced
        max_risk_amount = self.max_position_size * risk_per_trade
        shares = int(max_risk_amount / price)
        return max(1, min(shares, self.max_position_size))
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get strategy performance summary"""
        win_rate = (self.profitable_signals / self.total_signals * 100 
                   if self.total_signals > 0 else 0)
        
        return {
            'total_signals': self.total_signals,
            'profitable_signals': self.profitable_signals,
            'win_rate': win_rate,
            'recent_signals': self.signals[-10:] if len(self.signals) >= 10 else self.signals
        }


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


class BollingerBandStrategy(BaseStrategy):
    """
    Bollinger Band breakout/reversal strategy
    """
    
    def __init__(self, kite=None, params: Dict[str, Any] = None):
        default_params = {
            'bb_period': 20,
            'bb_std': 2,
            'strategy_type': 'reversal',  # 'reversal' or 'breakout'
            'min_confidence': 0.65
        }
        default_params.update(params or {})
        super().__init__(kite, default_params)
        
        self.bb_period = self.params['bb_period']
        self.bb_std = self.params['bb_std']
        self.strategy_type = self.params['strategy_type']
    
    def generate_signals(self, data: Dict[str, pd.DataFrame], current_date: datetime) -> List[Signal]:
        signals = []
        
        for symbol, df in data.items():
            if len(df) < self.bb_period:
                continue
            
            # Calculate Bollinger Bands
            bb_upper, bb_middle, bb_lower = self.ta.bollinger_bands(
                df['close'], self.bb_period, self.bb_std
            )
            
            current_price = df['close'].iloc[-1]
            current_upper = bb_upper.iloc[-1]
            current_lower = bb_lower.iloc[-1]
            current_middle = bb_middle.iloc[-1]
            
            if self.strategy_type == 'reversal':
                # Mean reversion: buy at lower band, sell at upper band
                if current_price <= current_lower:
                    signal = Signal(
                        symbol=symbol,
                        signal_type=SignalType.BUY,
                        confidence=0.7,
                        price=current_price,
                        timestamp=current_date,
                        reason=f"Price touched lower Bollinger Band: ${current_price:.2f} <= ${current_lower:.2f}"
                    )
                    signals.append(signal)
                
                elif current_price >= current_upper:
                    signal = Signal(
                        symbol=symbol,
                        signal_type=SignalType.SELL,
                        confidence=0.7,
                        price=current_price,
                        timestamp=current_date,
                        reason=f"Price touched upper Bollinger Band: ${current_price:.2f} >= ${current_upper:.2f}"
                    )
                    signals.append(signal)
            
            else:  # breakout strategy
                # Breakout: buy above upper band, sell below lower band
                if current_price > current_upper:
                    signal = Signal(
                        symbol=symbol,
                        signal_type=SignalType.BUY,
                        confidence=0.75,
                        price=current_price,
                        timestamp=current_date,
                        reason=f"Bullish breakout above upper Bollinger Band"
                    )
                    signals.append(signal)
                
                elif current_price < current_lower:
                    signal = Signal(
                        symbol=symbol,
                        signal_type=SignalType.SELL,
                        confidence=0.75,
                        price=current_price,
                        timestamp=current_date,
                        reason=f"Bearish breakdown below lower Bollinger Band"
                    )
                    signals.append(signal)
        
        return signals


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
