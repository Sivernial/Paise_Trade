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

from technical_indicators import TechnicalIndicators, PatternRecognition, TrendAnalysis
from core.backtesting import BacktestEngine

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