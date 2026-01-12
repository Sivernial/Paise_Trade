import pandas as pd
import numpy as np

def calculate_buying_pressure(df: pd.DataFrame) -> pd.Series:
    """
    Calculate Buying Pressure proxy from OHLCV data.
    
    Refined from OFI. Uses Close Location Value (CLV).
    Score = ((Close - Low) - (High - Close)) / (High - Low)
    Range: -1.0 (Close at Low) to +1.0 (Close at High)
    Weighted by Volume.
    """
    range_hl = (df['high'] - df['low']).replace(0, 1e-6)
    
    # Close Location Value (-1 to 1)
    clv = (((df['close'] - df['low']) - (df['high'] - df['close'])) / range_hl)
    
    # Volume Weighted Pressure
    pressure = clv * df['volume']
    
    # Normalize (Z-Score over rolling window)
    pressure_mean = pressure.rolling(window=50).mean()
    pressure_std = pressure.rolling(window=50).std()
    
    normalized_pressure = (pressure - pressure_mean) / (pressure_std + 1e-6)
    
    return normalized_pressure.fillna(0)

def calculate_volatility_regime(df: pd.DataFrame, window=20) -> pd.Series:
    """
    Calculate Volatility Regime (Low/Normal/High).
    Returns ratio of current volatility to long-term mean.
    """
    returns = np.log(df['close'] / df['close'].shift(1))
    current_vol = returns.rolling(window).std()
    long_vol = returns.rolling(window * 5).std()
    
    vol_ratio = current_vol / (long_vol + 1e-6)
    return vol_ratio.fillna(1.0)
