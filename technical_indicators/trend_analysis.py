"""
Trend Analysis Module

Trend identification and analysis tools for determining market direction,
support and resistance levels, and breakout detection.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Union
from .technical_analysis import TechnicalIndicators


class TrendAnalysis:
    """
    Trend identification and analysis tools
    """
    
    @staticmethod
    def trend_direction(data: pd.Series, short_period: int = 10, long_period: int = 20) -> pd.Series:
        """
        Determine trend direction using moving averages
        
        Args:
            data: Price series (typically close prices)
            short_period: Short-term moving average period
            long_period: Long-term moving average period
            
        Returns:
            Series with values: 1 (uptrend), -1 (downtrend), 0 (sideways)
        """
        ta = TechnicalIndicators()
        short_ma = ta.sma(data, short_period)
        long_ma = ta.sma(data, long_period)
        
        trend = pd.Series(0, index=data.index)
        trend[short_ma > long_ma] = 1
        trend[short_ma < long_ma] = -1
        
        return trend
    
    @staticmethod
    def trend_strength(data: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate trend strength using ADX-like methodology
        
        Returns:
            Series with trend strength values (0-100)
            >25 indicates strong trend, <20 indicates weak/sideways trend
        """
        # Calculate price changes
        high = data.rolling(window=2).max()
        low = data.rolling(window=2).min()
        close = data
        
        # Simplified trend strength calculation
        price_range = high - low
        directional_movement = abs(close.diff())
        
        # Smooth the values
        avg_range = price_range.rolling(window=period).mean()
        avg_movement = directional_movement.rolling(window=period).mean()
        
        # Calculate trend strength (0-100 scale)
        trend_strength = (avg_movement / avg_range * 100).fillna(0)
        trend_strength = trend_strength.clip(0, 100)
        
        return trend_strength
    
    @staticmethod
    def support_resistance(data: pd.Series, window: int = 20) -> Tuple[pd.Series, pd.Series]:
        """
        Identify support and resistance levels using rolling min/max
        
        Args:
            data: Price series
            window: Lookback period for identifying levels
            
        Returns:
            Tuple of (support_levels, resistance_levels)
        """
        support = data.rolling(window=window).min()
        resistance = data.rolling(window=window).max()
        
        return support, resistance
    
    @staticmethod
    def dynamic_support_resistance(data: pd.Series, window: int = 20, 
                                  sensitivity: float = 0.02) -> Tuple[pd.Series, pd.Series]:
        """
        Dynamic support and resistance using fractal-like approach
        
        Args:
            data: Price series
            window: Lookback window
            sensitivity: Minimum percentage move to qualify as support/resistance
            
        Returns:
            Tuple of (dynamic_support, dynamic_resistance)
        """
        # Find local minima and maxima
        local_min = data.rolling(window=window, center=True).min() == data
        local_max = data.rolling(window=window, center=True).max() == data
        
        # Create support and resistance series
        support = pd.Series(index=data.index, dtype=float)
        resistance = pd.Series(index=data.index, dtype=float)
        
        # Forward fill support and resistance levels
        last_support = None
        last_resistance = None
        
        for i, (idx, price) in enumerate(data.items()):
            # Update support
            if local_min.iloc[i] and (last_support is None or 
                                     abs(price - last_support) / last_support > sensitivity):
                last_support = price
            support.iloc[i] = last_support
            
            # Update resistance
            if local_max.iloc[i] and (last_resistance is None or 
                                     abs(price - last_resistance) / last_resistance > sensitivity):
                last_resistance = price
            resistance.iloc[i] = last_resistance
        
        return support.fillna(method='ffill'), resistance.fillna(method='ffill')
    
    @staticmethod
    def breakout_detection(data: pd.Series, support: pd.Series, 
                          resistance: pd.Series, threshold: float = 0.01) -> pd.Series:
        """
        Detect price breakouts above resistance or below support
        
        Args:
            data: Current price series
            support: Support level series
            resistance: Resistance level series
            threshold: Minimum percentage breakout to qualify
            
        Returns:
            Series with values: 1 (bullish breakout), -1 (bearish breakout), 0 (no breakout)
        """
        breakout = pd.Series(0, index=data.index)
        
        # Bullish breakout: price breaks above resistance
        bullish_breakout = data > resistance * (1 + threshold)
        breakout[bullish_breakout] = 1
        
        # Bearish breakout: price breaks below support
        bearish_breakout = data < support * (1 - threshold)
        breakout[bearish_breakout] = -1
        
        return breakout
    
    @staticmethod
    def trend_lines(data: pd.Series, window: int = 20, 
                   min_touches: int = 2) -> Tuple[pd.Series, pd.Series]:
        """
        Identify trend lines using linear regression on swing highs/lows
        
        Args:
            data: Price series
            window: Window for identifying swing points
            min_touches: Minimum touches required for valid trend line
            
        Returns:
            Tuple of (uptrend_line, downtrend_line)
        """
        # Find swing highs and lows
        highs = data.rolling(window=window, center=True).max() == data
        lows = data.rolling(window=window, center=True).min() == data
        
        uptrend_line = pd.Series(index=data.index, dtype=float)
        downtrend_line = pd.Series(index=data.index, dtype=float)
        
        # Simple trend line calculation (can be enhanced with proper regression)
        high_points = data[highs].dropna()
        low_points = data[lows].dropna()
        
        if len(high_points) >= min_touches:
            # Downtrend line through recent highs
            recent_highs = high_points.tail(min_touches)
            if len(recent_highs) >= 2:
                slope = (recent_highs.iloc[-1] - recent_highs.iloc[0]) / len(recent_highs)
                for i, idx in enumerate(data.index):
                    if idx >= recent_highs.index[0]:
                        pos = list(data.index).index(idx) - list(data.index).index(recent_highs.index[0])
                        downtrend_line.loc[idx] = recent_highs.iloc[0] + slope * pos
        
        if len(low_points) >= min_touches:
            # Uptrend line through recent lows
            recent_lows = low_points.tail(min_touches)
            if len(recent_lows) >= 2:
                slope = (recent_lows.iloc[-1] - recent_lows.iloc[0]) / len(recent_lows)
                for i, idx in enumerate(data.index):
                    if idx >= recent_lows.index[0]:
                        pos = list(data.index).index(idx) - list(data.index).index(recent_lows.index[0])
                        uptrend_line.loc[idx] = recent_lows.iloc[0] + slope * pos
        
        return uptrend_line, downtrend_line
    
    @staticmethod
    def zigzag(data: pd.Series, threshold: float = 0.05) -> pd.Series:
        """
        Create ZigZag indicator to identify significant price swings
        
        Args:
            data: Price series
            threshold: Minimum percentage move to qualify as swing
            
        Returns:
            Series with swing high/low values, NaN elsewhere
        """
        zigzag = pd.Series(index=data.index, dtype=float)
        
        if len(data) < 3:
            return zigzag
        
        # Initialize
        last_extreme = data.iloc[0]
        last_extreme_idx = data.index[0]
        trend = 0  # 1 for up, -1 for down
        
        zigzag.iloc[0] = last_extreme
        
        for i in range(1, len(data)):
            current_price = data.iloc[i]
            current_idx = data.index[i]
            
            if trend == 0:
                # Determine initial trend
                change = (current_price - last_extreme) / last_extreme
                if abs(change) >= threshold:
                    trend = 1 if change > 0 else -1
                    zigzag.loc[current_idx] = current_price
                    last_extreme = current_price
                    last_extreme_idx = current_idx
            
            elif trend == 1:  # Uptrend
                if current_price > last_extreme:
                    # New high
                    zigzag.loc[last_extreme_idx] = np.nan  # Remove previous high
                    zigzag.loc[current_idx] = current_price
                    last_extreme = current_price
                    last_extreme_idx = current_idx
                else:
                    # Check for reversal
                    change = (current_price - last_extreme) / last_extreme
                    if change <= -threshold:
                        # Trend reversal
                        trend = -1
                        zigzag.loc[current_idx] = current_price
                        last_extreme = current_price
                        last_extreme_idx = current_idx
            
            else:  # Downtrend
                if current_price < last_extreme:
                    # New low
                    zigzag.loc[last_extreme_idx] = np.nan  # Remove previous low
                    zigzag.loc[current_idx] = current_price
                    last_extreme = current_price
                    last_extreme_idx = current_idx
                else:
                    # Check for reversal
                    change = (current_price - last_extreme) / last_extreme
                    if change >= threshold:
                        # Trend reversal
                        trend = 1
                        zigzag.loc[current_idx] = current_price
                        last_extreme = current_price
                        last_extreme_idx = current_idx
        
        return zigzag