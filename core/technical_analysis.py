"""
Technical Analysis Library for Algorithmic Trading
Comprehensive collection of technical indicators and analysis tools
"""

import pandas as pd
import numpy as np
from typing import Union, Tuple, Optional
import warnings

class TechnicalIndicators:
    """
    Collection of technical indicators for trading analysis
    All methods are optimized for performance and handle edge cases
    """
    
    @staticmethod
    def sma(data: Union[pd.Series, list], period: int) -> pd.Series:
        """Simple Moving Average"""
        if isinstance(data, list):
            data = pd.Series(data)
        return data.rolling(window=period).mean()
    
    @staticmethod
    def ema(data: Union[pd.Series, list], period: int) -> pd.Series:
        """Exponential Moving Average"""
        if isinstance(data, list):
            data = pd.Series(data)
        return data.ewm(span=period).mean()
    
    @staticmethod
    def rsi(data: Union[pd.Series, list], period: int = 14) -> pd.Series:
        """Relative Strength Index"""
        if isinstance(data, list):
            data = pd.Series(data)
        
        delta = data.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def macd(data: Union[pd.Series, list], 
             fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD (Moving Average Convergence Divergence)"""
        if isinstance(data, list):
            data = pd.Series(data)
        
        exp1 = data.ewm(span=fast).mean()
        exp2 = data.ewm(span=slow).mean()
        
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(data: Union[pd.Series, list], 
                       period: int = 20, std_dev: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Bollinger Bands"""
        if isinstance(data, list):
            data = pd.Series(data)
        
        sma = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return upper_band, sma, lower_band
    
    @staticmethod
    def stochastic(high: Union[pd.Series, list], 
                  low: Union[pd.Series, list], 
                  close: Union[pd.Series, list], 
                  k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Stochastic Oscillator"""
        if isinstance(high, list):
            high = pd.Series(high)
        if isinstance(low, list):
            low = pd.Series(low)
        if isinstance(close, list):
            close = pd.Series(close)
        
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()
        
        k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
        d_percent = k_percent.rolling(window=d_period).mean()
        
        return k_percent, d_percent
    
    @staticmethod
    def atr(high: Union[pd.Series, list], 
            low: Union[pd.Series, list], 
            close: Union[pd.Series, list], 
            period: int = 14) -> pd.Series:
        """Average True Range"""
        if isinstance(high, list):
            high = pd.Series(high)
        if isinstance(low, list):
            low = pd.Series(low)
        if isinstance(close, list):
            close = pd.Series(close)
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        
        return atr
    
    @staticmethod
    def adx(high: Union[pd.Series, list], 
            low: Union[pd.Series, list], 
            close: Union[pd.Series, list], 
            period: int = 14) -> pd.Series:
        """Average Directional Index"""
        if isinstance(high, list):
            high = pd.Series(high)
        if isinstance(low, list):
            low = pd.Series(low)
        if isinstance(close, list):
            close = pd.Series(close)
        
        # Calculate directional movements
        dm_plus = high.diff()
        dm_minus = -low.diff()
        
        dm_plus[dm_plus < 0] = 0
        dm_minus[dm_minus < 0] = 0
        
        # True Range
        atr_val = TechnicalIndicators.atr(high, low, close, period)
        
        # Directional Indicators
        di_plus = 100 * dm_plus.rolling(window=period).mean() / atr_val
        di_minus = 100 * dm_minus.rolling(window=period).mean() / atr_val
        
        # ADX calculation
        dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus)
        adx = dx.rolling(window=period).mean()
        
        return adx
    
    @staticmethod
    def vwap(high: Union[pd.Series, list], 
             low: Union[pd.Series, list], 
             close: Union[pd.Series, list], 
             volume: Union[pd.Series, list]) -> pd.Series:
        """Volume Weighted Average Price"""
        if isinstance(high, list):
            high = pd.Series(high)
        if isinstance(low, list):
            low = pd.Series(low)
        if isinstance(close, list):
            close = pd.Series(close)
        if isinstance(volume, list):
            volume = pd.Series(volume)
        
        typical_price = (high + low + close) / 3
        cumulative_tpv = (typical_price * volume).cumsum()
        cumulative_volume = volume.cumsum()
        
        vwap = cumulative_tpv / cumulative_volume
        return vwap
    
    @staticmethod
    def williams_r(high: Union[pd.Series, list], 
                   low: Union[pd.Series, list], 
                   close: Union[pd.Series, list], 
                   period: int = 14) -> pd.Series:
        """Williams %R"""
        if isinstance(high, list):
            high = pd.Series(high)
        if isinstance(low, list):
            low = pd.Series(low)
        if isinstance(close, list):
            close = pd.Series(close)
        
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()
        
        williams_r = -100 * (highest_high - close) / (highest_high - lowest_low)
        return williams_r
    
    @staticmethod
    def momentum(data: Union[pd.Series, list], period: int = 10) -> pd.Series:
        """Price Momentum"""
        if isinstance(data, list):
            data = pd.Series(data)
        
        return data.diff(period)
    
    @staticmethod
    def roc(data: Union[pd.Series, list], period: int = 10) -> pd.Series:
        """Rate of Change"""
        if isinstance(data, list):
            data = pd.Series(data)
        
        return ((data - data.shift(period)) / data.shift(period)) * 100


class PatternRecognition:
    """
    Candlestick pattern recognition and chart patterns
    """
    
    @staticmethod
    def doji(open_prices: pd.Series, high: pd.Series, 
             low: pd.Series, close: pd.Series, threshold: float = 0.1) -> pd.Series:
        """Doji candlestick pattern"""
        body_size = abs(close - open_prices)
        range_size = high - low
        
        # Doji when body is very small relative to range
        is_doji = (body_size / range_size) < threshold
        return is_doji
    
    @staticmethod
    def hammer(open_prices: pd.Series, high: pd.Series, 
               low: pd.Series, close: pd.Series) -> pd.Series:
        """Hammer candlestick pattern"""
        body_size = abs(close - open_prices)
        upper_shadow = high - np.maximum(open_prices, close)
        lower_shadow = np.minimum(open_prices, close) - low
        
        # Hammer: small body, long lower shadow, small upper shadow
        is_hammer = (
            (lower_shadow > 2 * body_size) &
            (upper_shadow < body_size)
        )
        return is_hammer
    
    @staticmethod
    def engulfing_bullish(open_prices: pd.Series, close: pd.Series) -> pd.Series:
        """Bullish engulfing pattern"""
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
        """Bearish engulfing pattern"""
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


class TrendAnalysis:
    """
    Trend identification and analysis tools
    """
    
    @staticmethod
    def trend_direction(data: pd.Series, short_period: int = 10, long_period: int = 20) -> pd.Series:
        """
        Determine trend direction using moving averages
        Returns: 1 (uptrend), -1 (downtrend), 0 (sideways)
        """
        short_ma = TechnicalIndicators.sma(data, short_period)
        long_ma = TechnicalIndicators.sma(data, long_period)
        
        trend = pd.Series(0, index=data.index)
        trend[short_ma > long_ma] = 1
        trend[short_ma < long_ma] = -1
        
        return trend
    
    @staticmethod
    def support_resistance(data: pd.Series, window: int = 20) -> Tuple[pd.Series, pd.Series]:
        """
        Identify support and resistance levels using rolling min/max
        """
        support = data.rolling(window=window).min()
        resistance = data.rolling(window=window).max()
        
        return support, resistance
    
    @staticmethod
    def breakout_detection(data: pd.Series, support: pd.Series, 
                          resistance: pd.Series, threshold: float = 0.01) -> pd.Series:
        """
        Detect price breakouts above resistance or below support
        Returns: 1 (bullish breakout), -1 (bearish breakout), 0 (no breakout)
        """
        breakout = pd.Series(0, index=data.index)
        
        # Bullish breakout: price breaks above resistance
        bullish_breakout = data > resistance * (1 + threshold)
        breakout[bullish_breakout] = 1
        
        # Bearish breakout: price breaks below support
        bearish_breakout = data < support * (1 - threshold)
        breakout[bearish_breakout] = -1
        
        return breakout


class MarketVolatility:
    """
    Volatility analysis and risk metrics
    """
    
    @staticmethod
    def historical_volatility(data: pd.Series, period: int = 20, 
                            annualize: bool = True) -> pd.Series:
        """Calculate historical volatility"""
        returns = data.pct_change()
        volatility = returns.rolling(window=period).std()
        
        if annualize:
            volatility = volatility * np.sqrt(252)  # Assuming 252 trading days
        
        return volatility
    
    @staticmethod
    def value_at_risk(returns: pd.Series, confidence_level: float = 0.05) -> float:
        """Calculate Value at Risk (VaR)"""
        return np.percentile(returns, confidence_level * 100)
    
    @staticmethod
    def maximum_drawdown(data: pd.Series) -> float:
        """Calculate maximum drawdown"""
        cumulative = (1 + data.pct_change()).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        
        return drawdown.min()
    
    @staticmethod
    def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
        """Calculate Sharpe ratio"""
        excess_returns = returns - risk_free_rate
        return excess_returns.mean() / excess_returns.std() * np.sqrt(252)