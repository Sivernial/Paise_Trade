"""
Technical Analysis Library for Algorithmic Trading
Comprehensive collection of technical indicators and analysis tools with caching
"""

import pandas as pd
import numpy as np
from typing import Union, Tuple, Optional, Dict, Any
import warnings
import hashlib
from functools import lru_cache

class TechnicalIndicators:
    """
    Collection of technical indicators for trading analysis
    All methods are optimized for performance and handle edge cases
    Features intelligent caching to avoid redundant calculations
    """
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
    
    def _get_cache_key(self, data: Union[pd.Series, list], method_name: str, **kwargs) -> str:
        """Generate cache key for data and parameters"""
        if isinstance(data, list):
            data_hash = hashlib.md5(str(data).encode()).hexdigest()[:8]
        else:
            data_hash = hashlib.md5(f"{len(data)}{data.iloc[0] if len(data) > 0 else 0}{data.iloc[-1] if len(data) > 0 else 0}".encode()).hexdigest()[:8]
        
        params_str = "_".join([f"{k}_{v}" for k, v in sorted(kwargs.items())])
        return f"{method_name}_{data_hash}_{params_str}"
    
    def _get_cached_or_calculate(self, cache_key: str, calculation_func) -> pd.Series:
        """Get from cache or calculate and cache the result"""
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        result = calculation_func()
        self._cache[cache_key] = result
        return result
    
    def clear_cache(self):
        """Clear the indicator cache"""
        self._cache.clear()
    
    def sma(self, data: Union[pd.Series, list], period: int) -> pd.Series:
        """Simple Moving Average with caching and error handling"""
        try:
            # Input validation
            if period <= 0:
                raise ValueError(f"Period must be positive, got {period}")
            
            if isinstance(data, list):
                if len(data) == 0:
                    raise ValueError("Input data cannot be empty")
                series_data = pd.Series(data)
            else:
                if len(data) == 0:
                    raise ValueError("Input data cannot be empty")
                series_data = data.copy()
            
            if len(series_data) < period:
                raise ValueError(f"Insufficient data: need at least {period} points, got {len(series_data)}")
            
            # Check for invalid values
            if series_data.isna().all():
                raise ValueError("All data points are NaN")
            
            cache_key = self._get_cache_key(data, "sma", period=period)
            
            def calculate():
                result = series_data.rolling(window=period, min_periods=1).mean()
                
                # Handle edge cases
                if result.isna().all():
                    warnings.warn("SMA calculation resulted in all NaN values")
                
                return result
            
            return self._get_cached_or_calculate(cache_key, calculate)
            
        except Exception as e:
            warnings.warn(f"Error calculating SMA: {e}")
            # Return empty series with same index as input
            if isinstance(data, list):
                return pd.Series([np.nan] * len(data))
            else:
                return pd.Series([np.nan] * len(data), index=data.index)
    
    def ema(self, data: Union[pd.Series, list], period: int) -> pd.Series:
        """Exponential Moving Average with caching"""
        cache_key = self._get_cache_key(data, "ema", period=period)
        
        def calculate():
            if isinstance(data, list):
                series_data = pd.Series(data)
            else:
                series_data = data
            return series_data.ewm(span=period).mean()
        
        return self._get_cached_or_calculate(cache_key, calculate)
    
    def rsi(self, data: Union[pd.Series, list], period: int = 14) -> pd.Series:
        """Relative Strength Index with caching and error handling"""
        try:
            # Input validation
            if period <= 0:
                raise ValueError(f"Period must be positive, got {period}")
            
            if isinstance(data, list):
                if len(data) == 0:
                    raise ValueError("Input data cannot be empty")
                series_data = pd.Series(data)
            else:
                if len(data) == 0:
                    raise ValueError("Input data cannot be empty")
                series_data = data.copy()
            
            if len(series_data) < period + 1:  # Need extra point for diff calculation
                raise ValueError(f"Insufficient data: need at least {period + 1} points, got {len(series_data)}")
            
            cache_key = self._get_cache_key(data, "rsi", period=period)
            
            def calculate():
                delta = series_data.diff()
                
                # Handle potential division by zero
                gain = delta.where(delta > 0, 0)
                loss = -delta.where(delta < 0, 0)
                
                avg_gain = gain.rolling(window=period, min_periods=1).mean()
                avg_loss = loss.rolling(window=period, min_periods=1).mean()
                
                # Avoid division by zero
                rs = avg_gain / avg_loss.replace(0, np.nan)
                rsi = 100 - (100 / (1 + rs))
                
                # Fill NaN values at the beginning
                rsi = rsi.fillna(50)  # Neutral RSI for initial values
                
                return rsi
            
            return self._get_cached_or_calculate(cache_key, calculate)
            
        except Exception as e:
            warnings.warn(f"Error calculating RSI: {e}")
            # Return neutral RSI values (50)
            if isinstance(data, list):
                return pd.Series([50.0] * len(data))
            else:
                return pd.Series([50.0] * len(data), index=data.index)
    
    def macd(self, data: Union[pd.Series, list], 
             fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD (Moving Average Convergence Divergence) with caching"""
        cache_key = self._get_cache_key(data, "macd", fast=fast, slow=slow, signal=signal)
        
        def calculate():
            if isinstance(data, list):
                series_data = pd.Series(data)
            else:
                series_data = data
            
            exp1 = series_data.ewm(span=fast).mean()
            exp2 = series_data.ewm(span=slow).mean()
            
            macd_line = exp1 - exp2
            signal_line = macd_line.ewm(span=signal).mean()
            histogram = macd_line - signal_line
            
            return macd_line, signal_line, histogram
        
        return self._get_cached_or_calculate(cache_key, calculate)
    
    def bollinger_bands(self, data: Union[pd.Series, list], 
                       period: int = 20, std_dev: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Enhanced Bollinger Bands with caching
        
        Returns:
            Tuple of (upper_band, middle_band/SMA, lower_band)
        """
        cache_key = self._get_cache_key(data, "bollinger_bands", period=period, std_dev=std_dev)
        
        def calculate():
            if isinstance(data, list):
                series_data = pd.Series(data)
            else:
                series_data = data
            
            sma = series_data.rolling(window=period).mean()
            std = series_data.rolling(window=period).std()
            
            upper_band = sma + (std * std_dev)
            lower_band = sma - (std * std_dev)
            
            return upper_band, sma, lower_band
        
        return self._get_cached_or_calculate(cache_key, calculate)
    
    def bollinger_band_width(self, data: Union[pd.Series, list], 
                            period: int = 20, std_dev: float = 2) -> pd.Series:
        """
        Calculate Bollinger Band Width to measure volatility
        Lower values indicate low volatility (squeeze), higher values indicate high volatility
        """
        cache_key = self._get_cache_key(data, "bb_width", period=period, std_dev=std_dev)
        
        def calculate():
            upper, middle, lower = self.bollinger_bands(data, period, std_dev)
            width = (upper - lower) / middle
            return width
        
        return self._get_cached_or_calculate(cache_key, calculate)
    
    def bollinger_squeeze(self, data: Union[pd.Series, list], 
                         period: int = 20, std_dev: float = 2, 
                         squeeze_threshold: int = 10) -> pd.Series:
        """
        Detect Bollinger Band squeeze conditions
        
        Args:
            squeeze_threshold: Number of periods to look back for minimum bandwidth
            
        Returns:
            Boolean series indicating squeeze conditions
        """
        cache_key = self._get_cache_key(data, "bb_squeeze", 
                                      period=period, std_dev=std_dev, 
                                      threshold=squeeze_threshold)
        
        def calculate():
            bandwidth = self.bollinger_band_width(data, period, std_dev)
            
            # Squeeze when current bandwidth is the lowest in the lookback period
            rolling_min = bandwidth.rolling(window=squeeze_threshold).min()
            squeeze = bandwidth == rolling_min
            
            return squeeze
        
        return self._get_cached_or_calculate(cache_key, calculate)
    
    def bollinger_percent_b(self, data: Union[pd.Series, list], 
                           period: int = 20, std_dev: float = 2) -> pd.Series:
        """
        Calculate %B indicator - position of price within Bollinger Bands
        
        Returns:
            Values > 1: Above upper band
            Values 0-1: Between bands  
            Values < 0: Below lower band
        """
        cache_key = self._get_cache_key(data, "bb_percent_b", period=period, std_dev=std_dev)
        
        def calculate():
            if isinstance(data, list):
                series_data = pd.Series(data)
            else:
                series_data = data
                
            upper, middle, lower = self.bollinger_bands(series_data, period, std_dev)
            percent_b = (series_data - lower) / (upper - lower)
            
            return percent_b
        
        return self._get_cached_or_calculate(cache_key, calculate)
    
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
        
        prev_close = close.shift(1)
        
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        
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
        ta = TechnicalIndicators()
        short_ma = ta.sma(data, short_period)
        long_ma = ta.sma(data, long_period)
        
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