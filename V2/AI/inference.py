
import os
import joblib
import numpy as np
import tensorflow as tf
from .deep_model import DeepQuantModel
import logging

logger = logging.getLogger(__name__)

class DeepInferenceEngine:
    """
    Handles inference for the Deep Learning Model (Shen et al. 2020).
    Manages loading, scaling, feature selection, and prediction.
    """
    
    def __init__(self, model_path=None, scaler_path=None):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Paths
        if model_path is None:
            model_path = os.path.join(self.base_dir, 'Models', 'deep_model.h5')
        if scaler_path is None:
            scaler_path = os.path.join(self.base_dir, 'scaler.pkl')
            
        self.model = self._load_model(model_path)
        self.scaler = self._load_scaler(scaler_path)
        
        # RFE Selected Indices (from Training Log)
        # [Z_Score, Beta, Hurst, BB_Width, RSI_A, RSI_B, Volatility_A, Spread_Dist_MA, Vol_Factor, Z_Vel, Kurt, Sector]
        self.rfe_indices = [0, 1, 3, 4, 5, 6, 7, 9, 11, 14, 16, 18]
        
    def _load_model(self, path):
        try:
            # Load custom object if needed, or standard Keras load
            # Since DeepQuantModel is a wrapper, we load the raw .h5 model
            if not os.path.exists(path):
                logger.error(f"Deep Model not found at {path}")
                return None
            return tf.keras.models.load_model(path)
        except Exception as e:
            logger.error(f"Error loading Deep Model: {e}")
            return None
            
    def _load_scaler(self, path):
        try:
            if not os.path.exists(path):
                logger.error(f"Scaler not found at {path}")
                return None
            return joblib.load(path)
        except Exception as e:
            logger.error(f"Error loading Scaler: {e}")
            return None

    def predict(self, feature_sequence):
        """
        Predict probability of trade success.
        feature_sequence: List or Array of shape (30, 19) (Raw Features)
        """
        if self.model is None or self.scaler is None:
            return 0.5 # Neutral if model broken
            
        feature_sequence = np.array(feature_sequence)
        
        # 1. Validation
        if feature_sequence.shape != (30, 19):
            logger.warning(f"Invalid feature shape: {feature_sequence.shape}, expected (30, 19)")
            return 0.0
            
        try:
            # 2. Scale (StandardScaler expects 2D: Samples x Features)
            # We treat the sequence as 'samples' for the scaler transform, 
            # assuming the scaler was fit on flattened data.
            scaled_seq = self.scaler.transform(feature_sequence)
            
            # 3. Feature Selection (RFE)
            # Select specific columns
            selected_seq = scaled_seq[:, self.rfe_indices]
            
            # 4. Reshape for LSTM (Batch, TimeSteps, Features)
            # Shape: (1, 30, 12)
            input_tensor = selected_seq.reshape(1, 30, len(self.rfe_indices))
            
            # 5. Predict
            prob = self.model.predict(input_tensor, verbose=0)[0][0]
            return prob
            
        except Exception as e:
            logger.error(f"Prediction Error: {e}")
            return 0.0
