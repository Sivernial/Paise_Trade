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

def calculate_pca_residuals(data: pd.DataFrame, n_components: int = 1) -> pd.DataFrame:
    """
    Extract residuals of a basket of stocks after removing common factors using PCA.
    data: DataFrame where columns are asset returns (log returns preferred).
    n_components: Number of principal components to treat as common factors (usually 1 for 'Market' or 'Sector' factor).
    Returns: DataFrame of residuals.
    """
    from sklearn.decomposition import PCA
    
    # Work with log returns to ensure stationarity
    # If data is prices, we should convert locally or assume it's returns
    # Assuming data is log returns for this utility
    
    # 1. Standardize (De-mean and unit variance)
    mu = data.mean()
    sigma = data.std()
    standardized_data = (data - mu) / sigma
    
    # 2. PCA
    pca = PCA(n_components=n_components)
    factors = pca.fit_transform(standardized_data) # [Time, N_Components]
    
    # 3. Reconstruct the "Common" part
    # standardized = Factors * Components + Residuals
    common_part = factors @ pca.components_
    
    # 4. Residuals = Standardized - Common
    residuals = standardized_data - common_part
    
    return residuals

class MarketRegimeDetector:
    """
    Detects market regimes (e.g. Low Vol, High Vol, Trending) using GMM clustering.
    """
    def __init__(self, n_regimes: int = 2):
        from sklearn.mixture import GaussianMixture
        self.model = GaussianMixture(n_components=n_regimes, random_state=42)
        self.is_fitted = False
        
    def fit_predict(self, data: pd.Series) -> np.ndarray:
        """
        Fit the model on historical returns/volatility and return regime labels.
        """
        X = data.values.reshape(-1, 1)
        self.model.fit(X)
        self.is_fitted = True
        return self.model.predict(X)
    
    def predict(self, val: float) -> int:
        """
        Predict regime for a single new value.
        """
        if not self.is_fitted:
            return 0
        return int(self.model.predict(np.array([[val]]))[0])

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate Average True Range (ATR).
    df: DataFrame with 'high', 'low', 'close' columns.
    """
    high = df['high']
    low = df['low']
    close = df['close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate Average Directional Index (ADX).
    df: DataFrame with 'high', 'low', 'close' columns.
    ADX > 25 usually indicates a strong trend.
    """
    high = df['high']
    low = df['low']
    close = df['close']
    
    plus_dm = high.diff()
    minus_dm = low.diff()
    
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    minus_dm = abs(minus_dm)
    
    # Simple TR calculation
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Smoothed components
    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()
    return adx

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index (RSI)."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_vwap(df: pd.DataFrame) -> pd.Series:
    """
    Calculate Volume Weighted Average Price (VWAP).
    Resets daily if index is DatetimeIndex.
    """
    df = df.copy()
    df['tp'] = (df['high'] + df['low'] + df['close']) / 3
    df['tpv'] = df['tp'] * df['volume']
    
    if isinstance(df.index, pd.DatetimeIndex):
        # Group by date for daily reset
        date_series = df.index.date
        cum_tpv = df.groupby(date_series)['tpv'].cumsum()
        cum_vol = df.groupby(date_series)['volume'].cumsum()
        return cum_tpv / cum_vol
    
    return df['tpv'].cumsum() / df['volume'].cumsum()

def round_to_tick(price: float, tick_size: float = 0.05) -> float:
    """Round a price to the nearest tick size (e.g., 0.05 for NSE)."""
    if price is None: return None
    # Convert to float to handle potential numpy types
    price_val = float(price)
    return round(round(price_val / tick_size) * tick_size, 2)

def calculate_volume_profile(df: pd.DataFrame, bins: int = 50, va_percent: float = 0.70) -> dict:
    """
    Calculate Volume Profile (VAH, VAL, POC).
    df: 1-minute data for a single day.
    Returns: {vah, val, poc}
    """
    if df is None or df.empty:
        return {'vah': None, 'val': None, 'poc': None}
    
    prices = df['close']
    volumes = df['volume']
    
    min_p, max_p = prices.min(), prices.max()
    if min_p == max_p:
        return {'vah': min_p, 'val': min_p, 'poc': min_p}
    
    # Create Bins
    bin_size = (max_p - min_p) / bins
    price_bins = np.linspace(min_p, max_p, bins + 1)
    
    # Calculate volume per bin
    # We use digits to assign each price to a bin
    bin_indices = np.digitize(prices, price_bins) - 1
    # Ensure indices are within [0, bins-1]
    bin_indices = np.clip(bin_indices, 0, bins - 1)
    
    vol_profile = np.zeros(bins)
    for i, vol in zip(bin_indices, volumes):
        vol_profile[i] += vol
        
    # POC: Point of Control
    poc_idx = np.argmax(vol_profile)
    poc = (price_bins[poc_idx] + price_bins[poc_idx + 1]) / 2
    
    # Value Area (VA)
    total_vol = vol_profile.sum()
    va_vol_target = total_vol * va_percent
    
    va_indices = [poc_idx]
    current_va_vol = vol_profile[poc_idx]
    
    up_idx = poc_idx + 1
    down_idx = poc_idx - 1
    
    while current_va_vol < va_vol_target:
        vol_up = vol_profile[up_idx] if up_idx < bins else 0
        vol_down = vol_profile[down_idx] if down_idx >= 0 else 0
        
        if up_idx >= bins and down_idx < 0:
            break
            
        if vol_up >= vol_down and up_idx < bins:
            current_va_vol += vol_up
            va_indices.append(up_idx)
            up_idx += 1
        elif down_idx >= 0:
            current_va_vol += vol_down
            va_indices.append(down_idx)
            down_idx -= 1
        else:
            # Safety break
            break
            
    val = price_bins[min(va_indices)]
    vah = price_bins[max(va_indices) + 1]
    
    return {
        'vah': round(vah, 2),
        'val': round(val, 2),
        'poc': round(poc, 2)
    }
