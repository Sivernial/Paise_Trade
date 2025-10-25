"""
Pattern Recognition Module

Candlestick pattern recognition and chart patterns for technical analysis.
Includes common bullish and bearish reversal patterns.
"""

import pandas as pd
import numpy as np
from typing import Union


class PatternRecognition:
    """
    Candlestick pattern recognition and chart patterns
    """
    
    @staticmethod
    def doji(open_prices: pd.Series, high: pd.Series, 
             low: pd.Series, close: pd.Series, threshold: float = 0.1) -> pd.Series:
        """
        Doji candlestick pattern
        
        Characteristics:
        - Very small body (open ≈ close)
        - Indicates indecision in the market
        - Can signal potential reversals
        """
        body_size = abs(close - open_prices)
        range_size = high - low
        
        # Avoid division by zero
        range_size = range_size.replace(0, 0.0001)
        
        # Doji when body is very small relative to range
        is_doji = (body_size / range_size) < threshold
        return is_doji
    
    @staticmethod
    def hammer(open_prices: pd.Series, high: pd.Series, 
               low: pd.Series, close: pd.Series) -> pd.Series:
        """
        Hammer candlestick pattern
        
        Characteristics:
        - Small body at the top of the trading range
        - Long lower shadow (at least 2x body size)
        - Small or no upper shadow
        - Bullish reversal pattern
        """
        body_size = abs(close - open_prices)
        upper_shadow = high - np.maximum(open_prices, close)
        lower_shadow = np.minimum(open_prices, close) - low
        
        # Hammer: small body, long lower shadow, small upper shadow
        is_hammer = (
            (lower_shadow > 2 * body_size) &
            (upper_shadow < body_size) &
            (body_size > 0)  # Ensure there's some body
        )
        return is_hammer
    
    @staticmethod
    def hanging_man(open_prices: pd.Series, high: pd.Series, 
                    low: pd.Series, close: pd.Series) -> pd.Series:
        """
        Hanging Man candlestick pattern
        
        Same shape as hammer but appears after uptrend - bearish reversal
        """
        # Same pattern as hammer, but context determines if it's hanging man
        return PatternRecognition.hammer(open_prices, high, low, close)
    
    @staticmethod
    def shooting_star(open_prices: pd.Series, high: pd.Series, 
                      low: pd.Series, close: pd.Series) -> pd.Series:
        """
        Shooting Star candlestick pattern
        
        Characteristics:
        - Small body at the bottom of the trading range
        - Long upper shadow (at least 2x body size)
        - Small or no lower shadow
        - Bearish reversal pattern
        """
        body_size = abs(close - open_prices)
        upper_shadow = high - np.maximum(open_prices, close)
        lower_shadow = np.minimum(open_prices, close) - low
        
        # Shooting star: small body, long upper shadow, small lower shadow
        is_shooting_star = (
            (upper_shadow > 2 * body_size) &
            (lower_shadow < body_size) &
            (body_size > 0)  # Ensure there's some body
        )
        return is_shooting_star
    
    @staticmethod
    def engulfing_bullish(open_prices: pd.Series, close: pd.Series) -> pd.Series:
        """
        Bullish Engulfing pattern
        
        Characteristics:
        - Previous candle is bearish (red)
        - Current candle is bullish (green)
        - Current candle completely engulfs previous candle's body
        - Strong bullish reversal signal
        """
        prev_open = open_prices.shift(1)
        prev_close = close.shift(1)
        
        # Previous candle bearish, current candle bullish and engulfs previous
        bullish_engulfing = (
            (prev_close < prev_open) &  # Previous bearish
            (close > open_prices) &     # Current bullish
            (open_prices < prev_close) &  # Current opens below prev close
            (close > prev_open)         # Current closes above prev open
        )
        return bullish_engulfing
    
    @staticmethod
    def engulfing_bearish(open_prices: pd.Series, close: pd.Series) -> pd.Series:
        """
        Bearish Engulfing pattern
        
        Characteristics:
        - Previous candle is bullish (green)
        - Current candle is bearish (red)
        - Current candle completely engulfs previous candle's body
        - Strong bearish reversal signal
        """
        prev_open = open_prices.shift(1)
        prev_close = close.shift(1)
        
        # Previous candle bullish, current candle bearish and engulfs previous
        bearish_engulfing = (
            (prev_close > prev_open) &  # Previous bullish
            (close < open_prices) &     # Current bearish
            (open_prices > prev_close) &  # Current opens above prev close
            (close < prev_open)         # Current closes below prev open
        )
        return bearish_engulfing
    
    @staticmethod
    def morning_star(open_prices: pd.Series, high: pd.Series, 
                     low: pd.Series, close: pd.Series) -> pd.Series:
        """
        Morning Star pattern (simplified 3-candle pattern)
        
        Characteristics:
        - First candle: large bearish candle
        - Second candle: small body (doji or spinning top)
        - Third candle: large bullish candle
        - Bullish reversal pattern
        """
        # Simplified version checking for the pattern
        prev2_open = open_prices.shift(2)
        prev2_close = close.shift(2)
        prev1_open = open_prices.shift(1)
        prev1_close = close.shift(1)
        
        # First candle: bearish
        first_bearish = prev2_close < prev2_open
        
        # Second candle: small body
        second_small = abs(prev1_close - prev1_open) < abs(prev2_close - prev2_open) * 0.3
        
        # Third candle: bullish
        third_bullish = close > open_prices
        
        # Gap conditions (simplified)
        gap_down = prev1_open < prev2_close
        gap_up = open_prices > prev1_close
        
        morning_star = (
            first_bearish &
            second_small &
            third_bullish &
            gap_down &
            gap_up
        )
        
        return morning_star
    
    @staticmethod
    def evening_star(open_prices: pd.Series, high: pd.Series, 
                     low: pd.Series, close: pd.Series) -> pd.Series:
        """
        Evening Star pattern (simplified 3-candle pattern)
        
        Characteristics:
        - First candle: large bullish candle
        - Second candle: small body (doji or spinning top)
        - Third candle: large bearish candle
        - Bearish reversal pattern
        """
        # Simplified version checking for the pattern
        prev2_open = open_prices.shift(2)
        prev2_close = close.shift(2)
        prev1_open = open_prices.shift(1)
        prev1_close = close.shift(1)
        
        # First candle: bullish
        first_bullish = prev2_close > prev2_open
        
        # Second candle: small body
        second_small = abs(prev1_close - prev1_open) < abs(prev2_close - prev2_open) * 0.3
        
        # Third candle: bearish
        third_bearish = close < open_prices
        
        # Gap conditions (simplified)
        gap_up = prev1_open > prev2_close
        gap_down = open_prices < prev1_close
        
        evening_star = (
            first_bullish &
            second_small &
            third_bearish &
            gap_up &
            gap_down
        )
        
        return evening_star