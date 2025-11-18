import pandas as pd
import numpy as np
from typing import Tuple, List
from .dynamicConfig import get_config

class DynamicIndicators:
    
    @staticmethod
    def volatility(data: pd.Series, config: dict = None) -> pd.Series:
        cfg = config or get_config('volatility')
        period = cfg.get('period', 20)
        annualize = cfg.get('annualize', True)
        
        returns = data.pct_change()
        vol = returns.rolling(window=period).std()
        
        if annualize:
            vol = vol * np.sqrt(252)
        
        return vol
    
    @staticmethod
    def momentum(data: pd.Series, config: dict = None) -> pd.Series:
        cfg = config or get_config('momentum')
        period = cfg.get('period', 10)
        return ((data - data.shift(period)) / data.shift(period)) * 100
    
    @staticmethod
    def trend_strength(data: pd.Series, config: dict = None) -> pd.Series:
        cfg = config or get_config('trend_strength')
        short_period = cfg.get('short_period', 10)
        long_period = cfg.get('long_period', 50)
        
        short_ma = data.rolling(window=short_period).mean()
        long_ma = data.rolling(window=long_period).mean()
        
        trend = ((short_ma - long_ma) / long_ma) * 100
        return trend
    
    @staticmethod
    def volume_profile(volume: pd.Series, config: dict = None) -> pd.Series:
        cfg = config or get_config('volume_profile')
        period = cfg.get('period', 20)
        
        avg_volume = volume.rolling(window=period).mean()
        volume_ratio = volume / avg_volume
        return volume_ratio
    
    @staticmethod
    def support_resistance(high: pd.Series, low: pd.Series, 
                          config: dict = None) -> Tuple[List[float], List[float]]:
        cfg = config or get_config('support_resistance')
        lookback = cfg.get('lookback', 50)
        num_levels = cfg.get('num_levels', 3)
        
        recent_high = high.tail(lookback)
        recent_low = low.tail(lookback)
        
        resistance_levels = recent_high.nlargest(num_levels).tolist()
        support_levels = recent_low.nsmallest(num_levels).tolist()
        
        return support_levels, resistance_levels
    
    @staticmethod
    def volatility_ratio(data: pd.Series, config: dict = None) -> pd.Series:
        cfg = config or get_config('volatility_ratio')
        short_period = cfg.get('short_period', 10)
        long_period = cfg.get('long_period', 30)
        
        short_vol = data.rolling(window=short_period).std()
        long_vol = data.rolling(window=long_period).std()
        
        return short_vol / long_vol.replace(0, 0.0001)
    
    @staticmethod
    def price_channels(high: pd.Series, low: pd.Series, 
                      config: dict = None) -> Tuple[pd.Series, pd.Series]:
        cfg = config or get_config('price_channels')
        period = cfg.get('period', 20)
        
        upper_channel = high.rolling(window=period).max()
        lower_channel = low.rolling(window=period).min()
        
        return upper_channel, lower_channel
    
    @staticmethod
    def relative_volume(volume: pd.Series, config: dict = None) -> pd.Series:
        cfg = config or get_config('volume_profile')
        period = cfg.get('period', 20)
        
        avg_volume = volume.rolling(window=period).mean()
        rel_volume = (volume / avg_volume - 1) * 100
        return rel_volume

