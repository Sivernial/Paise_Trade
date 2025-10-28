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
                raise ValueError("Period must be positive")
            
            # Convert to pandas Series if needed
            if isinstance(data, list):
                data = pd.Series(data)
            
            if len(data) < period:
                warnings.warn(f"Data length ({len(data)}) is less than period ({period})")
                return pd.Series(dtype=float, index=data.index if hasattr(data, 'index') else range(len(data)))
            
            # Generate cache key
            cache_key = self._get_cache_key(data, "sma", period=period)
            
            def calculate():
                return data.rolling(window=period, min_periods=1).mean()
            
            return self._get_cached_or_calculate(cache_key, calculate)
            
        except Exception as e:
            print(f"Error calculating SMA: {e}")
            return pd.Series(dtype=float, index=data.index if hasattr(data, 'index') else range(len(data)))
    
    def ema(self, data: Union[pd.Series, list], period: int) -> pd.Series:
        """Exponential Moving Average with caching"""
        if isinstance(data, list):
            data = pd.Series(data)
        
        cache_key = self._get_cache_key(data, "ema", period=period)
        
        def calculate():
            return data.ewm(span=period, adjust=False).mean()
        
        return self._get_cached_or_calculate(cache_key, calculate)
    
    # technical_indicators/technical_analysis.py

    def rsi(self, data: Union[pd.Series, list], period: int = 14) -> pd.Series:
        """
        Relative Strength Index with proper calculation and caching.
        Returns NaNs until there are at least period+1 points (no warnings).
        """
        try:
            if isinstance(data, list):
                data = pd.Series(data)

            # Not enough data: return NaNs aligned to input index
            if len(data) < period + 1:
                return pd.Series(np.nan, index=data.index if hasattr(data, 'index') else range(len(data)), dtype=float)

            cache_key = self._get_cache_key(data, "rsi", period=period)

            def calculate():
                delta = data.diff()
                gain = delta.where(delta > 0, 0.0)
                loss = -delta.where(delta < 0, 0.0)
                avg_gain = gain.ewm(span=period, adjust=False).mean()
                avg_loss = loss.ewm(span=period, adjust=False).mean()
                rs = avg_gain / avg_loss.replace(0, np.nan)
                rsi = 100 - (100 / (1 + rs))
                return rsi

            return self._get_cached_or_calculate(cache_key, calculate)

        except Exception as e:
            print(f"Error calculating RSI: {e}")
            return pd.Series(np.nan, index=data.index if hasattr(data, 'index') else range(len(data)), dtype=float)
    
    def macd(self, data: Union[pd.Series, list], 
             fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD (Moving Average Convergence Divergence) with caching"""
        if isinstance(data, list):
            data = pd.Series(data)
        
        cache_key = self._get_cache_key(data, "macd", fast=fast_period, slow=slow_period, signal=signal_period)
        
        def calculate():
            ema_fast = self.ema(data, fast_period)
            ema_slow = self.ema(data, slow_period)
            
            macd_line = ema_fast - ema_slow
            signal_line = self.ema(macd_line, signal_period)
            histogram = macd_line - signal_line
            
            return macd_line, signal_line, histogram
        
        return self._get_cached_or_calculate(cache_key, calculate)
    
    def bollinger_bands(self, data: Union[pd.Series, list], 
                       period: int = 20, std_dev: float = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Bollinger Bands with caching"""
        if isinstance(data, list):
            data = pd.Series(data)
        
        cache_key = self._get_cache_key(data, "bollinger", period=period, std=std_dev)
        
        def calculate():
            sma = self.sma(data, period)
            std = data.rolling(window=period).std()
            
            upper_band = sma + (std * std_dev)
            lower_band = sma - (std * std_dev)
            
            return upper_band, sma, lower_band
        
        return self._get_cached_or_calculate(cache_key, calculate)
    
    def bollinger_band_width(self, data: Union[pd.Series, list], 
                           period: int = 20, std_dev: float = 2) -> pd.Series:
        """Bollinger Band Width (measure of volatility)"""
        if isinstance(data, list):
            data = pd.Series(data)
        
        cache_key = self._get_cache_key(data, "bb_width", period=period, std=std_dev)
        
        def calculate():
            upper, middle, lower = self.bollinger_bands(data, period, std_dev)
            return (upper - lower) / middle
        
        return self._get_cached_or_calculate(cache_key, calculate)
    
    def bollinger_squeeze(self, data: Union[pd.Series, list], 
                         bb_period: int = 20, bb_std: float = 2, 
                         kc_period: int = 20, kc_mult: float = 1.5,
                         squeeze_lookback: int = 10) -> pd.Series:
        """
        Bollinger Band Squeeze detection
        True when BB are inside Keltner Channels (low volatility)
        """
        if isinstance(data, list):
            data = pd.Series(data)
        
        cache_key = self._get_cache_key(data, "bb_squeeze", 
                                       bb_period=bb_period, bb_std=bb_std,
                                       kc_period=kc_period, kc_mult=kc_mult,
                                       lookback=squeeze_lookback)
        
        def calculate():
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = self.bollinger_bands(data, bb_period, bb_std)
            
            # Simple squeeze detection using band width
            bb_width = self.bollinger_band_width(data, bb_period, bb_std)
            bb_width_ma = bb_width.rolling(window=squeeze_lookback).mean()
            
            # Squeeze when current width is below average
            squeeze = bb_width < bb_width_ma * 0.8  # 20% below average
            
            return squeeze
        
        return self._get_cached_or_calculate(cache_key, calculate)
    
    def bollinger_percent_b(self, data: Union[pd.Series, list], 
                           period: int = 20, std_dev: float = 2) -> pd.Series:
        """
        %B indicator - shows where price is relative to Bollinger Bands
        %B = (Price - Lower Band) / (Upper Band - Lower Band)
        """
        if isinstance(data, list):
            data = pd.Series(data)
        
        cache_key = self._get_cache_key(data, "percent_b", period=period, std=std_dev)
        
        def calculate():
            upper, middle, lower = self.bollinger_bands(data, period, std_dev)
            percent_b = (data - lower) / (upper - lower)
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
        
        true_range = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
        atr = true_range.rolling(window=period).mean()
        
        return atr
    
    @staticmethod
    def adx(high: Union[pd.Series, list], 
            low: Union[pd.Series, list], 
            close: Union[pd.Series, list], 
            period: int = 14) -> pd.Series:
        """Average Directional Index (simplified version)"""
        if isinstance(high, list):
            high = pd.Series(high)
        if isinstance(low, list):
            low = pd.Series(low)
        if isinstance(close, list):
            close = pd.Series(close)
        
        # Calculate directional movement
        dm_plus = high.diff()
        dm_minus = -low.diff()
        
        # Only keep positive values
        dm_plus[dm_plus < 0] = 0
        dm_minus[dm_minus < 0] = 0
        
        # Calculate ATR for normalization
        atr_values = TechnicalIndicators.atr(high, low, close, period)
        
        # Calculate directional indicators
        di_plus = 100 * (dm_plus.rolling(window=period).mean() / atr_values)
        di_minus = 100 * (dm_minus.rolling(window=period).mean() / atr_values)
        
        # Calculate ADX (simplified)
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
        cumulative_volume = volume.cumsum()
        cumulative_price_volume = (typical_price * volume).cumsum()
        
        vwap = cumulative_price_volume / cumulative_volume
        
        return vwap
    
    def momentum(self, data: Union[pd.Series, list], period: int = 10) -> pd.Series:
        """Price Momentum indicator"""
        if isinstance(data, list):
            data = pd.Series(data)
        
        cache_key = self._get_cache_key(data, "momentum", period=period)
        
        def calculate():
            return ((data - data.shift(period)) / data.shift(period)) * 100
        
        return self._get_cached_or_calculate(cache_key, calculate)