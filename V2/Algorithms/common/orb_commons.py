import pandas as pd
import numpy as np
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def compute_rvol(df: pd.DataFrame, lookback_days: int = 20) -> pd.Series:
    if len(df) < lookback_days:
        return pd.Series(1.0, index=df.index)
    
    try:
        rvol = pd.Series(index=df.index, dtype=float)
        
        for idx in df.index:
            # ✅ FIX: Only use data from PAST days (exclude current day)
            past_data = df[df.index.date < idx.date()]
            
            if len(past_data) == 0:
                rvol[idx] = 1.0
                continue
            
            # Get same time-of-day bars from past days
            same_tod = past_data[past_data.index.time == idx.time()]
            
            if len(same_tod) == 0:
                rvol[idx] = 1.0
                continue
            
            # Use most recent N days
            recent_tod = same_tod.tail(lookback_days)
            avg_vol = recent_tod['volume'].mean()
            current_vol = df.loc[idx, 'volume']
            
            if avg_vol > 0:
                rvol[idx] = current_vol / avg_vol
            else:
                rvol[idx] = 1.0
        
        return rvol
    except Exception as e:
        logger.warning(f"RVOL calculation failed: {e}, returning 1.0")
        return pd.Series(1.0, index=df.index)

def compute_vwap_std(df: pd.DataFrame) -> pd.Series:
    """Compute VWAP standard deviation for a single day"""
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
    
    squared_diff = ((typical_price - vwap) ** 2 * df['volume']).cumsum()
    cum_vol = df['volume'].cumsum().replace(0, np.nan)
    variance = squared_diff / cum_vol
    return np.sqrt(variance)

