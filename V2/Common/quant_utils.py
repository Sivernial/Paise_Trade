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

class KalmanFilterReg:
    """
    Kalman Filter for estimating time-varying regression slope (beta).
    Model: y = beta * x + e
    State: beta (random walk)
    """
    def __init__(self, delta=1e-5, R=1e-3):
        # delta = Process noise variance (flexibility of beta)
        # R = Measurement noise variance
        self.delta = delta
        self.R = R
        self.P = np.zeros(2) # Covariance matrix (diagonal)
        self.state = 0.0 # Initial beta
        self.is_initialized = False

    def update(self, y: float, x: float) -> float:
        """
        Update state with new observation and return filtered beta.
        y: Dependent variable (Asset A)
        x: Independent variable (Asset B)
        """
        if not self.is_initialized:
            # Initialize with OLS or first observation ratio
            self.state = y / x if x != 0 else 0
            self.P = 1.0 # High uncertainty
            self.is_initialized = True
            return self.state

        # Prediction Step
        # beta(t|t-1) = beta(t-1|t-1) (Random Walk)
        # P(t|t-1) = P(t-1|t-1) + delta
        beta_pred = self.state
        P_pred = self.P + self.delta

        # Update Step
        # y_pred = beta_pred * x
        y_pred = beta_pred * x
        error = y - y_pred # Measurement residual

        # Kalman Gain
        # S = x * P_pred * x + R
        S = x**2 * P_pred + self.R
        K = P_pred * x / S

        # State Update
        self.state = beta_pred + K * error
        self.P = (1 - K * x) * P_pred

        return self.state

def calculate_dynamic_beta_kalman(series_y: pd.Series, series_x: pd.Series, 
                                  delta=1e-5) -> pd.Series:
    """
    Batch calculate dynamic beta sequence for backtesting using Kalman Filter.
    Returns: Series of betas
    """
    kf = KalmanFilterReg(delta=delta)
    betas = []
    
    for y, x in zip(series_y.values, series_x.values):
        beta = kf.update(y, x)
        betas.append(beta)
        
    return pd.Series(betas, index=series_y.index)

def calculate_hurst(ts: pd.Series) -> float:
    """
    Calculate Hurst Exponent to determine long-term memory.
    H < 0.5: Mean Reverting (Good for Pairs)
    H = 0.5: Random Walk
    H > 0.5: Trending
    """
    try:
        ts = ts.values if hasattr(ts, 'values') else np.array(ts)
        lags = range(2, 20)
        tau = [np.sqrt(np.std(np.subtract(ts[lag:], ts[:-lag]))) for lag in lags]
        poly = np.polyfit(np.log(lags), np.log(tau), 1)
        return poly[0] * 2.0
    except:
        return 0.5

def count_zero_crossings(spread: pd.Series) -> int:
    """
    Count how many times the spread crosses its own mean.
    Higher crossings = Higher trade frequency opportunity.
    """
    try:
        if len(spread) < 2: return 0
        mean_val = spread.mean()
        centered = spread - mean_val
        # Sign changes indicate crossing
        crossings = np.where(np.diff(np.sign(centered)))[0]
        return len(crossings)
    except:
        return 0
