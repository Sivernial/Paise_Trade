import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def compute_rvol(df: pd.DataFrame, lookback_days: int = 20) -> pd.Series:
    """Compute relative volume compared to same time of day over past N days"""
    if len(df) < lookback_days:
        return pd.Series(1.0, index=df.index)
    
    try:
        tod = df.index.time
        grouped = df.groupby([df.index.date, tod])['volume'].sum().unstack(level=0)
        
        if grouped.empty or len(grouped.columns) < 2:
            return pd.Series(1.0, index=df.index)
        
        lookback_cols = min(lookback_days, len(grouped.columns))
        avg_vol_by_tod = grouped.iloc[:, -lookback_cols:].mean(axis=1)
        
        rvol = pd.Series(index=df.index, dtype=float)
        for idx in df.index:
            current_vol = df.loc[idx, 'volume']
            avg_vol = avg_vol_by_tod.get(idx.time(), np.nan)
            if pd.notna(avg_vol) and avg_vol > 0:
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

