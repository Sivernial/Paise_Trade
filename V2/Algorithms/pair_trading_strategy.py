from typing import Dict, List, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
from .base_strategy import BaseStrategy
from Common.enums import SignalType
from Common import Signal
from Common.quant_utils import calculate_adf_statistic, KalmanFilterReg
from Common.risk_manager import RiskManager
from Market_Intelligence.sentiment_analyzer import MarketIntelligence
from Technical_Indicators.static import StaticIndicators
from AI.feature_engineer import FeatureEngineer
from AI.inference import DeepInferenceEngine
import joblib
import os
from collections import deque
import logging

logger = logging.getLogger(__name__)

class PairTradingStrategy(BaseStrategy):
    
    def __init__(self, params: dict = None):
        default_params = {
            'pairs': [], # List of tuples [('AssetA', 'AssetB')]
            'z_score_threshold': 2.0,
            'lookback_window': 40, # Tuned to 40 for balance
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
        self.stop_loss = 0.05 # Added
        self.take_profit = 0.02 # Added
        
        # Risk Manager
        self.risk_manager = RiskManager()
        # Market Intelligence (Public Info)
        self.market_intel = MarketIntelligence()
        
        # Registry for Kalman Filters (one per pair)
        self.kf_registry = {pair: KalmanFilterReg() for pair in self.pairs} # Updated
            
        self.last_processed: Dict[Tuple[str, str], datetime] = {}
        self.latest_state: Dict[Tuple[str, str], dict] = {} # For Dashboard Logging
        
        # Feature History for LSTM (30 steps) # Added
        self.feature_history = {pair: deque(maxlen=30) for pair in self.pairs} # Added
        
        # Load AI Model (Deep Learning) # Updated
        try:
            self.ai_model = DeepInferenceEngine()
            logger.info("✅ Deep Learning Model Loaded")
        except Exception as e:
            logger.error(f"Failed to load AI Model: {e}")
            self.ai_model = None
        
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
                        current_date: datetime, capital: float = 100000) -> List[Signal]:
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
                
                if self.ai_model: # Check if Deep Learning model exists
                    # 4. AI Verification (Deep Learning)
                    ai_score = 0.5 # Default if not enough data or model not used
                    if self.ai_model and asset_a in data: # Ensure ai_model is loaded and data is available
                        # Need sector context (using imported helper or passing it in)
                        # Ideally config has it, or we rely on default=0 if not easily available here
                        # Let's import the helper to be robust
                        from AI.generate_data import get_sector_id # Lazy import
                        sector_id = get_sector_id(asset_a, asset_b)
                        
                        # Extract features using the full window_a_df and window_b_df
                        features = FeatureEngineer.extract_features(
                            window_a_df, window_b_df, spread_series, current_z, 
                            beta, adf_stat, sector_id
                        )
                        
                        if features:
                            feat_vec = list(features.values())
                            
                            # Add to history
                            self.feature_history[(asset_a, asset_b)].append(feat_vec)
                            
                            # Only predict if we have full sequence (30 steps)
                            if len(self.feature_history[(asset_a, asset_b)]) == 30:
                                seq = list(self.feature_history[(asset_a, asset_b)])
                                ai_score = self.ai_model.predict(seq)
                            else:
                                ai_score = 0.5 # Warming up, not enough history for prediction
                    ai_confidence = ai_score # Use the deep learning model's score as confidence
                         
                # Log State
                self.latest_state[pair_key] = {
                    'z_score': current_z,
                    'beta': beta,
                    'spread': spread_series.iloc[-1],
                    'ai_confidence': ai_confidence,
                    'timestamp': current_date
                }
                
                if self.ai_model and raw_signal != 0:
                     # Filter logic from before
                     if ai_confidence < 0.7: 
                         continue 

                # Beta Guardrails (Avoid extreme leverage)
                if not (0.2 <= beta <= 4.0):
                    continue

                # RISK MANAGEMENT
                # Calculate ATR for Asset A
                atr_a = StaticIndicators.atr(
                    window_a_df['high'], 
                    window_a_df['low'], 
                    window_a_df['close'], 
                    period=14
                ).iloc[-1]
                
                # Calculate Quantity using Risk Manager (Dynamic Sizing)
                # We size Asset A based on volatility, and assume Asset B balances it.
                # Note: We technically should check portfolio correlation here, but strategy is pair-isolated.
                qty_a = self.risk_manager.calculate_size(capital, price_a, atr_a)
                
                # Ensure minimum viable quantity
                qty_a = max(1, qty_a)
                
                # Balance leg B
                qty_b = max(1, int(round(qty_a * beta)))

                # Generate Signals
                if current_z > self.z_threshold and is_cointegrated:
                    # Market Intelligence: Scale Size based on Sentiment
                    # If sentiment is very negative for the asset we are buying (Leg B), reduce size.
                    # Here we check both. If either is "Extreme Fear", we reduce size.
                    
                    sent_a = self.market_intel.get_sentiment(f"{asset_a} share news")
                    sent_b = self.market_intel.get_sentiment(f"{asset_b} share news")
                    
                    # Default Multiplier
                    size_multiplier = 1.0
                    
                    # If selling A (Leg 1), negative sentiment on A is actually good? 
                    # No, usually in Pair Trading we want Mean Reversion, not momentum. 
                    # Extreme news often breaks correlation. So we reduce risk on ANY extreme news.
                    
                    if sent_a['score'] < -0.5 or sent_b['score'] < -0.5:
                        size_multiplier = 0.5 # Half size
                        logger.info(f"⚠️ Reduced Size (0.5x) due to Negative Sentiment: {asset_a}={sent_a['score']:.2f}, {asset_b}={sent_b['score']:.2f}")
                    elif sent_a['score'] < -0.2 or sent_b['score'] < -0.2:
                        size_multiplier = 0.75 # 75% size
                        
                    # Apply Multiplier
                    final_qty_a = max(1, int(qty_a * size_multiplier))
                    final_qty_b = max(1, int(qty_b * size_multiplier))

                    signals.append(Signal(asset_a, SignalType.SELL, price_a, current_date, 
                                        quantity=final_qty_a, reason=f"Z={current_z:.2f} Beta={beta:.2f} Sent={size_multiplier}x"))
                    signals.append(Signal(asset_b, SignalType.BUY, price_b, current_date, 
                                        quantity=final_qty_b, reason=f"Z={current_z:.2f} Beta={beta:.2f} Sent={size_multiplier}x"))
                                        
                elif current_z < -self.z_threshold and is_cointegrated:
                     # Market Intelligence Scaling
                    sent_a = self.market_intel.get_sentiment(f"{asset_a} share news")
                    sent_b = self.market_intel.get_sentiment(f"{asset_b} share news")
                    
                    size_multiplier = 1.0
                    if sent_a['score'] < -0.5 or sent_b['score'] < -0.5:
                        size_multiplier = 0.5
                        logger.info(f"⚠️ Reduced Size (0.5x) due to Negative Sentiment")
                    elif sent_a['score'] < -0.2 or sent_b['score'] < -0.2:
                        size_multiplier = 0.75

                    final_qty_a = max(1, int(qty_a * size_multiplier))
                    final_qty_b = max(1, int(qty_b * size_multiplier))

                    signals.append(Signal(asset_a, SignalType.BUY, price_a, current_date, 
                                        quantity=final_qty_a, reason=f"Z={current_z:.2f} Beta={beta:.2f} Sent={size_multiplier}x"))
                    signals.append(Signal(asset_b, SignalType.SELL, price_b, current_date, 
                                        quantity=final_qty_b, reason=f"Z={current_z:.2f} Beta={beta:.2f} Sent={size_multiplier}x"))
                
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
