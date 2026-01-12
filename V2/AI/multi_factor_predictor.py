import pandas as pd
import numpy as np
import logging
import joblib
import os
from typing import Dict, List, Optional
from sklearn.ensemble import RandomForestRegressor as XGBRegressor

logger = logging.getLogger(__name__)

class MultiFactorPredictor:
    """
    Predicts future residual values based on historical window of factors.
    Uses XGBoost as a high-performance baseline for 5-min alpha.
    """
    def __init__(self, model_path: str = "AI/v3_predictor.joblib"):
        self.model_path = model_path
        self.model = None
        
    def load_model(self):
        if os.path.exists(self.model_path):
            self.model = joblib.load(self.model_path)
            logger.info("V3 Predictor model loaded.")
        else:
            logger.warning(f"V3 Predictor model not found at {self.model_path}. Please train first.")

    def extract_features(self, residuals: pd.Series, volume: pd.Series) -> pd.DataFrame:
        """
        Creates features for prediction:
        - Lags: t-1 to t-5
        - Volatility: 5, 20 rolling
        - Volume Momentum: Vol / MA(Vol)
        """
        df = pd.DataFrame({'res': residuals})
        
        # Lags
        for i in range(1, 6):
            df[f'lag_{i}'] = df['res'].shift(i)
            
        # Volatility
        df['vol_5'] = df['res'].rolling(5).std()
        df['vol_20'] = df['res'].rolling(20).std()
        
        # Volume features
        df['vol_delta'] = volume.diff()
        df['rvol'] = volume / volume.rolling(20).mean()
        
        # Velocity / Acceleration
        df['velocity'] = df['res'].diff()
        df['acceleration'] = df['velocity'].diff()
        
        return df.dropna()

    def predict(self, features: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            return np.zeros(len(features))
        return self.model.predict(features)

    def train(self, X: pd.DataFrame, y: pd.Series):
        """Train the model on historical residuals."""
        self.model = XGBRegressor(n_estimators=100, max_depth=5, n_jobs=-1, random_state=42)
        self.model.fit(X, y)
        joblib.dump(self.model, self.model_path)
        logger.info(f"V3 Predictor trained and saved to {self.model_path}")
