import numpy as np
import pandas as pd
from typing import Tuple, Union

def calculate_hedge_ratio(series_y: pd.Series, series_x: pd.Series) -> float:
    """
    Calculate Hedge Ratio using OLS (y = beta * x + alpha)
    Using basic numpy for efficiency.
    """
    if len(series_y) != len(series_x):
        min_len = min(len(series_y), len(series_x))
        series_y = series_y.iloc[-min_len:]
        series_x = series_x.iloc[-min_len:]
        
    # Use numpy for OLS
    # polyfit returns [slope, intercept]
    beta, alpha = np.polyfit(series_x, series_y, 1)
    return beta

def calculate_adf_statistic(x: Union[pd.Series, np.ndarray]) -> float:
    """
    Calculate simplified ADF statistic using Numpy.
    Run regression: delta_x = alpha + gamma * x_lag + error
    The t-statistic of gamma is the ADF score.
    """
    x = np.array(x)
    x_lag = x[:-1]
    x_delta = np.diff(x)
    
    # Regression of x_delta on x_lag and constant
    # Design matrix X: column of 1s and x_lag
    X = np.vstack([np.ones(len(x_lag)), x_lag]).T
    y = x_delta
    
    # Beta = (X'X)^-1 X'y
    try:
        XtX = X.T @ X
        XtX_inv = np.linalg.inv(XtX)
        coeffs = XtX_inv @ X.T @ y
        gamma = coeffs[1]
        
        # Standard error calculation for t-stat
        residuals = y - X @ coeffs
        if len(y) <= 2:
            return 0.0
            
        sigma_sq = np.sum(residuals**2) / (len(y) - 2)
        var_gamma = sigma_sq * XtX_inv[1, 1]
        se_gamma = np.sqrt(var_gamma)
        
        if se_gamma == 0:
            return 0.0
            
        adf_stat = gamma / se_gamma
        return adf_stat
    except Exception:
        return 0.0

def calculate_half_life(spread: pd.Series) -> float:
    """
    Calculate Half-Life of mean reversion.
    Based on Ornstein-Uhlenbeck process: dx = -theta * (x - mu) * dt + sigma * dW
    Discrete: x(t) - x(t-1) = alpha + beta * x(t-1) + error
    theta = -log(1 + beta)
    Half-life = -log(2) / log(1 + beta)
    """
    spread_lag = spread.shift(1)
    spread_ret = spread - spread_lag
    spread_lag = spread_lag.iloc[1:]
    spread_ret = spread_ret.iloc[1:]
    
    if len(spread_lag) < 2:
        return 0.0
        
    # Regression of spread_ret on spread_lag (with constant)
    beta, alpha = np.polyfit(spread_lag, spread_ret, 1)
    
    if beta >= 0:
        return np.inf # Not mean reverting
        
    try:
        half_life = -np.log(2) / np.log(1 + beta)
        return half_life
    except:
        return np.inf
