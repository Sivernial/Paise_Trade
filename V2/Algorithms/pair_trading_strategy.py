from typing import Dict, List, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
from .base_strategy import BaseStrategy
from Common.enums import SignalType
from Common import Signal
from Common import Signal
from Common.quant_utils import calculate_adf_statistic, KalmanFilterReg
from AI.feature_engineer import FeatureEngineer
import joblib
import os
import logging

logger = logging.getLogger(__name__)

class PairTradingStrategy(BaseStrategy):
    
    def __init__(self, params: dict = None):
        default_params = {
            'pairs': [], # List of tuples [('AssetA', 'AssetB')]
            'z_score_threshold': 2.0,
            'lookback_window': 20,
            'stop_loss_z': 4.0,
            'take_profit_z': 0.0,
            'min_confidence': 0.8
        }
        if params:
            default_params.update(params)
        super().__init__(default_params)
        
        self.pairs = self.params['pairs']
        self.z_threshold = self.params['z_score_threshold']
        self.lookback = self.params['lookback_window']
        self.stop_z = self.params['stop_loss_z']
        self.exit_z = self.params['take_profit_z']
        
        # Registry for Kalman Filters (one per pair)
        self.kf_registry = {}
        for pair in self.pairs:
            # Initialize with small delta for adaptivity
            self.kf_registry[pair] = KalmanFilterReg(delta=1e-4, R=1e-3)
            
        self.last_processed: Dict[Tuple[str, str], datetime] = {}
        
        # Load AI Model
        self.model = None
        model_path = os.path.join(os.path.dirname(__file__), '..', 'AI', 'model.pkl')
        if os.path.exists(model_path):
            try:
                self.model = joblib.load(model_path)
                logger.info(f"✅ AI Model loaded from {model_path}")
            except Exception as e:
                logger.error(f"Failed to load AI model: {e}")
        else:
            logger.warning("⚠️ AI Model not found. Running in heuristic mode.")
        
    def calculate_spread_zscore(self, series_a: pd.Series, series_b: pd.Series) -> Tuple[float, float]:
        """
        Calculate Spread and Z-Score
        Spread = log(A) - log(B)
        Z-Score = (Spread - Mean) / Std
        """
        if len(series_a) != len(series_b):
            min_len = min(len(series_a), len(series_b))
            series_a = series_a.iloc[-min_len:]
            series_b = series_b.iloc[-min_len:]
        
        # Use log prices for spread to handle different price scales better
        log_a = np.log(series_a)
        log_b = np.log(series_b)
        
        spread = log_a - log_b
        
        mean_spread = spread.rolling(window=self.lookback).mean()
        std_spread = spread.rolling(window=self.lookback).std()
        
        z_score = (spread - mean_spread) / std_spread
        
        return spread.iloc[-1], z_score.iloc[-1]
    
    def calculate_dynamic_zscore(self, series_a: pd.Series, series_b: pd.Series) -> Tuple[float, float, float, float]:
        """
        Calculate Spread and Z-Score using Dynamic Hedge Ratio
        Spread = A - beta * B
        """
        if len(series_a) != len(series_b):
            min_len = min(len(series_a), len(series_b))
            series_a = series_a.iloc[-min_len:]
            series_b = series_b.iloc[-min_len:]
        
        # Calculate dynamic hedge ratio on the window
        beta = calculate_hedge_ratio(series_a, series_b)
        
        # Calculate spread
        spread = series_a - beta * series_b
        
        # Z-Score
        mean_spread = spread.mean()
        std_spread = spread.std()
        
        z_score = (spread.iloc[-1] - mean_spread) / std_spread if std_spread != 0 else 0
        
        # ADF Test on the spread
        adf_stat = calculate_adf_statistic(spread)
        
        return spread.iloc[-1], z_score, beta, adf_stat

    def generate_signals(self, data: Dict[str, pd.DataFrame], 
                        current_date: datetime) -> List[Signal]:
        signals = []
        
        for asset_a, asset_b in self.pairs:
            if asset_a not in data or asset_b not in data:
                logger.warning(f"Missing data for pair {asset_a}-{asset_b}")
                continue
                
            df_a = data[asset_a]
            df_b = data[asset_b]
            
            if len(df_a) < self.lookback or len(df_b) < self.lookback:
                continue
            
            try:
                # Use longer history for ADF and Hedge Ratio calculation to be stable
                # Using 2x lookback for calculation window if available, else lookback
                calc_window = min(len(df_a), self.lookback * 2)
                
                # We need OHLC for features, so take full DF slice
                window_a_df = df_a.iloc[-calc_window:]
                window_b_df = df_b.iloc[-calc_window:]
                
                # For calc, we need series
                window_a = window_a_df['close']
                window_b = window_b_df['close']
                
                # Update Kalman Filter to get Dynamic Beta
                pair_key = (asset_a, asset_b)
                current_time = current_date
                
                # Ensure we process each bar only once
                last_time = self.last_processed.get(pair_key)
                kf = self.kf_registry[pair_key]
                
                price_a = df_a.iloc[-1]['close']
                price_b = df_b.iloc[-1]['close']
                
                if last_time != current_time:
                    beta = kf.update(price_a, price_b)
                    self.last_processed[pair_key] = current_time
                else:
                    beta = kf.state

                # 3. Calculate Spread and Z-Score
                # Spread = A - Beta * B
                # Note: Z-Score still needs history. We construct a synthetic spread history?
                # For simplicity/robustness: Use current beta on lookback window to check Z-score deviation
                spread_series = window_a - beta * window_b
                
                mean_spread = spread_series.mean()
                std_spread = spread_series.std()
                
                if std_spread == 0: continue
                
                current_z = (spread_series.iloc[-1] - mean_spread) / std_spread
                
                # OPTIMIZATION: ADF Calculation is slow, maybe skip every other bar?
                # For now keeping it for correctness.
                adf_stat = calculate_adf_statistic(spread_series)
                
                # 4. Entry Logic
                is_cointegrated = adf_stat < -1.94
                
                # AI FILTERING
                ai_confidence = 1.0 # Default if no model
                raw_signal = 0
                
                if current_z > self.z_threshold: raw_signal = 1
                elif current_z < -self.z_threshold: raw_signal = -1
                
                if self.model and raw_signal != 0:
                    # Extract Features
                    # Pass DataFrames!
                    features = FeatureEngineer.extract_features(
                        window_a_df, window_b_df, spread_series, current_z, beta, adf_stat
                    )
                    if features:
                        features['Signal_Dir'] = raw_signal
                        # Prepare DF for prediction
                        X_pred = pd.DataFrame([features])
                        # Ensure columns match training (handled by DF names if consistent)
                        # Predict
                        probs = self.model.predict_proba(X_pred)[0]
                        ai_confidence = probs[1] # Prob of Class 1 (Profit)
                        
                        # Filter
                        if ai_confidence < 0.6: # Threshold
                            # logger.info(f"🤖 AI REJECTED Signal {asset_a}-{asset_b} (Conf: {ai_confidence:.2f})")
                            continue # SKIP TRADE

                # Beta Guardrails (Avoid extreme leverage)
                if not (0.2 <= beta <= 4.0):
                    continue

                base_qty = 5
                qty_a = base_qty
                qty_b = max(1, int(round(base_qty * beta)))

                # Generate Signals
                if current_z > self.z_threshold and is_cointegrated:
                    signals.append(Signal(asset_a, SignalType.SELL, price_a, current_date, 
                                        quantity=qty_a, reason=f"Z={current_z:.2f} Beta={beta:.2f} AI={ai_confidence:.2f}"))
                    signals.append(Signal(asset_b, SignalType.BUY, price_b, current_date, 
                                        quantity=qty_b, reason=f"Z={current_z:.2f} Beta={beta:.2f} AI={ai_confidence:.2f}"))
                                        
                elif current_z < -self.z_threshold and is_cointegrated:
                    signals.append(Signal(asset_a, SignalType.BUY, price_a, current_date, 
                                        quantity=qty_a, reason=f"Z={current_z:.2f} Beta={beta:.2f} AI={ai_confidence:.2f}"))
                    signals.append(Signal(asset_b, SignalType.SELL, price_b, current_date, 
                                        quantity=qty_b, reason=f"Z={current_z:.2f} Beta={beta:.2f} AI={ai_confidence:.2f}"))
                
                # Exit Logic (Mean Reversion)
                elif abs(current_z) <= 0.5:
                     for symbol, pos in [(asset_a, self.positions.get(asset_a)), 
                                       (asset_b, self.positions.get(asset_b))]:
                         if pos and pos.quantity != 0:
                             signal_type = SignalType.SELL if pos.quantity > 0 else SignalType.BUY
                             signals.append(Signal(symbol, signal_type, 
                                                 df_a.iloc[-1]['close'] if symbol == asset_a else df_b.iloc[-1]['close'], 
                                                 current_date, reason=f"Mean Reversion (Z={current_z:.2f})"))
                     
            except Exception as e:
                logger.error(f"Error processing pair {asset_a}-{asset_b}: {e}")
                continue
                
        return signals
