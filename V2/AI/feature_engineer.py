import pandas as pd
import numpy as np
from sklearn.feature_selection import RFE
from sklearn.linear_model import LogisticRegression
from sklearn.decomposition import PCA

class FeatureEngineer:
    """
    Generates technical features for Machine Learning models.
    """
    
    @staticmethod
    def calculate_rsi(series: pd.Series, period=14) -> pd.Series:
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)

    @staticmethod
    def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period=14) -> pd.Series:
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr.fillna(0)
    
    @staticmethod
    def calculate_slope(series: pd.Series, period=5) -> pd.Series:
        """Calculate linear regression slope over a rolling window"""
        def slope_func(y):
            if len(y) < 2: return 0
            x = np.arange(len(y))
            slope, _ = np.polyfit(x, y, 1)
            return slope
            
        return series.rolling(window=period).apply(slope_func, raw=True).fillna(0)

    @staticmethod
    def calculate_hurst(series: pd.Series, max_lag=20) -> float:
        """
        Calculate Hurst Exponent to test for mean reversion.
        H < 0.5: Mean Reverting
        H ~ 0.5: Geometric Brownian Motion (Random Walk)
        H > 0.5: Trending
        """
        try:
            if len(series) < max_lag:
                return 0.5
                
            lags = range(2, max_lag)
            tau = [np.sqrt(np.std(np.subtract(series[lag:], series[:-lag]))) for lag in lags]
            poly = np.polyfit(np.log(lags), np.log(tau), 1)
            return poly[0] * 2.0
        except:
            return 0.5

    @staticmethod
    def extract_features(df_a: pd.DataFrame, df_b: pd.DataFrame, 
                        spread: pd.Series, z_score: float, 
                        beta: float, adf_stat: float, sector_id: int = 0) -> dict:
        """
        Extract features for a specific point in time (latest).
        """
        # Ensure sufficient history
        if len(df_a) < 50:
            return {}
            
        # 1. Price Features
        rsi_a = FeatureEngineer.calculate_rsi(df_a['close']).iloc[-1]
        rsi_b = FeatureEngineer.calculate_rsi(df_b['close']).iloc[-1]
        
        # 2. Volatility
        atr_a = FeatureEngineer.calculate_atr(df_a['high'], df_a['low'], df_a['close']).iloc[-1]
        vol_a = atr_a / df_a['close'].iloc[-1] # Normalized ATR
        
        # 3. Spread Features
        spread_mom = spread.diff().iloc[-1]
        spread_ma = spread.rolling(20).mean().iloc[-1] # Slower MA
        spread_std = spread.rolling(20).std().iloc[-1]
        dist_ma = (spread.iloc[-1] - spread_ma) / (spread_std + 1e-6) # Z-Score like
        
        # Bollinger Band Width (Squeeze/Expansion)
        bb_width = (2 * 2 * spread_std) / (abs(spread_ma) + 1e-6)
        
        # Hurst Exponent (Reversion Strength) w/ small optimization window
        # Using last 100 bars for Hurst
        hurst = FeatureEngineer.calculate_hurst(spread.iloc[-100:].values)
        
        # 4. Correlation (Rolling)
        corr_14 = df_a['close'].rolling(14).corr(df_b['close']).iloc[-1]
        
        # 5. Volume Features [NEW]
        vol_a_ma = df_a['volume'].rolling(20).mean().iloc[-1]
        vol_bf = df_a['volume'].iloc[-1] / (vol_a_ma + 1) # Relative Volume
        
        # 6. Time Features [NEW]
        ts = df_a.index[-1]
        hour = ts.hour
        is_opening = 1 if hour < 10 else 0
        is_closing = 1 if hour >= 15 else 0
        
        # 7. Lag Features [NEW] (Velocity of Z-Score)
        # Using Z-Score directly if passed as history? 
        # Ideally we want Z-Score change over last 3 bars
        # Since we only get current Z, we can approx with Spread change magnitude normalized
        z_velocity = spread_mom / (atr_a + 1) # Approx
        
        # 8. Statistical Moments (Distribution Shape) [WorldQuant: Complex Posterior]
        rolling_window = spread.iloc[-30:] # Last 30 bars
        skew = rolling_window.skew()
        kurt = rolling_window.kurt()
        
        # 9. Cycle Analysis (FFT) [WorldQuant: Multi-level Cycles]
        # Extract dominant frequency magnitude
        fft_vals = np.abs(np.fft.rfft(rolling_window.values))
        # Skip DC component (0)
        dominant_cycle_mag = np.max(fft_vals[1:]) if len(fft_vals) > 1 else 0
        
        features = {
            'Z_Score': z_score,
            'Beta': beta,
            'ADF_Stat': adf_stat,
            'Hurst': hurst,
            'BB_Width': bb_width,
            'RSI_A': rsi_a,
            'RSI_B': rsi_b,
            'Volatility_A': vol_a,
            'Spread_Momentum': spread_mom,
            'Spread_Dist_MA': dist_ma,
            'Correlation': corr_14,
            'Volume_Factor': vol_bf,
            'Is_Opening': is_opening,
            'Is_Closing': is_closing,
            'Z_Velocity': z_velocity,
            'Spread_Skew': skew,
            'Spread_Kurt': kurt,
            'Cycle_Mag': dominant_cycle_mag,
            'Sector_ID': sector_id
        }
        
        # Handle nan/inf
        for k, v in features.items():
            if np.isnan(v) or np.isinf(v):
                features[k] = 0.0
                
        return features

    @staticmethod
    def perform_rfe(X, y, n_features=10):
        """
        Recursive Feature Elimination (Shen et al. 2020).
        Selects best features by recursively removing weakest ones.
        """
        model = LogisticRegression(solver='liblinear')
        rfe = RFE(model, n_features_to_select=n_features)
        fit = rfe.fit(X, y)
        selected_cols = X.columns[fit.support_]
        return selected_cols

    @staticmethod
    def perform_pca(X, n_components=0.95):
        """
        Principal Component Analysis.
        Reduces dimensionality while keeping variance.
        """
        pca = PCA(n_components=n_components)
        X_pca = pca.fit_transform(X)
        return X_pca, pca
