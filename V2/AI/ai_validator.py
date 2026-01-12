import numpy as np
import pandas as pd
import joblib
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class AIValidator:
    """
    ML-based signal validator to reduce false positives in pair trading.
    Uses features derived from spread and market conditions.
    """
    
    def __init__(self, model_path: str = None):
        if model_path is None:
            model_path = os.path.join(os.path.dirname(__file__), "model.joblib")
        
        self.model_path = model_path
        self.model = None
        self.is_loaded = False
        self._load_model()
        
    def _load_model(self):
        try:
            if os.path.exists(self.model_path):
                self.model = joblib.load(self.model_path)
                self.is_loaded = True
                logger.info(f"AI Model loaded from {self.model_path}")
            else:
                logger.warning(f"AI Model not found at {self.model_path}. Signals will be passthrough.")
        except Exception as e:
            logger.error(f"Error loading AI model: {e}")

    def extract_features(self, spread_series: pd.Series, beta: float, rsi: float, hurst: float, sentiment: float) -> Dict[str, float]:
        """
        Extract features for the ML model.
        Must match the features used during training.
        """
        # Velocity (Last 5 bars)
        velocity = spread_series.diff(5).iloc[-1]
        
        # Volatility
        vol = spread_series.rolling(20).std().iloc[-1]
        
        # Distance from mean
        rolling_mean = spread_series.rolling(40).mean().iloc[-1]
        dist_mean = spread_series.iloc[-1] - rolling_mean if not np.isnan(rolling_mean) else 0
        
        # Acceleration
        acceleration = spread_series.diff().diff().iloc[-1]
        
        return {
            'velocity': float(velocity) if not np.isnan(velocity) else 0.0,
            'volatility': float(vol) if not np.isnan(vol) else 0.0,
            'dist_mean': float(dist_mean),
            'acceleration': float(acceleration) if not np.isnan(acceleration) else 0.0,
            'beta': float(beta),
            'rsi': float(rsi),
            'hurst': float(hurst),
            'sentiment': float(sentiment)
        }

    def predict_confidence(self, features_dict: Dict[str, float]) -> float:
        """
        Returns a confidence score between 0 and 1.
        If no model is loaded, returns 1.0 (passthrough).
        """
        if not self.is_loaded or self.model is None:
            return 1.0
            
        try:
            # Convert dict to array in fixed order
            feature_cols = ['velocity', 'volatility', 'dist_mean', 'acceleration', 'beta', 'rsi', 'hurst', 'sentiment']
            features = np.array([features_dict[col] for col in feature_cols]).reshape(1, -1)
            # For classifiers like XGBoost or RandomForest
            if hasattr(self.model, "predict_proba"):
                probs = self.model.predict_proba(features)
                return float(probs[0][1]) # Assuming class 1 is "Success"
            else:
                return float(self.model.predict(features))
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return 0.5 # Neutral on error
