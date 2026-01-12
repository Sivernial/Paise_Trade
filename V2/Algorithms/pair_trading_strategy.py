from typing import Dict, List, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
from .base_strategy import BaseStrategy
from Common.enums import SignalType
from Common import Signal
from Common.quant_utils import calculate_adf_statistic, KalmanFilterReg
from Common.risk_manager import RiskManager
from Common.ou_process import OUProcess
from Market_Intelligence.sentiment_analyzer import MarketIntelligence
from Technical_Indicators.static import StaticIndicators
from AI.ai_validator import AIValidator
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
        self.stop_loss = 0.05
        self.take_profit = 0.02
        
        # Intraday Parameters
        self.time_stop = self.params.get('time_stop') # "HH:MM" format
        self.entry_cutoff = self.params.get('entry_cutoff') # "HH:MM" format
        
        # Risk thresholds
        self.atr_stop_mult = self.params.get('atr_stop_mult', 2.5)
        self.rsi_period = 14
        self.rsi_entry_high = 60
        self.rsi_entry_low = 40
        
        # Risk Manager
        self.risk_manager = RiskManager()
        # Market Intelligence (Public Info)
        self.market_intel = MarketIntelligence()
        
        # Registry for Kalman Filters (one per pair)
        self.kf_registry = {pair: KalmanFilterReg() for pair in self.pairs}
        
        # Registry for OU Process (one per pair)
        self.ou_registry = {pair: OUProcess() for pair in self.pairs}
        self.ou_fitted = {pair: False for pair in self.pairs}
        self.ou_is_mr = {pair: True for pair in self.pairs}
            
        self.last_processed: Dict[Tuple[str, str], datetime] = {}
        self.latest_state: Dict[Tuple[str, str], dict] = {} # For Dashboard Logging
        self.entry_spreads: Dict[Tuple[str, str], float] = {} # Tracks spread at time of entry
        
        # AI Validator
        self.ai_validator = AIValidator()
        self.min_ai_confidence = self.params.get('min_ai_confidence', 0.6)
        
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
            
            # 0. Time Based Exit (Intraday)
            if self.time_stop:
                self.check_time_exit(current_date, asset_a, asset_b, signals, df_a, df_b)
                # If exit signals generated, stop processing for this pair
                if any(s.symbol in (asset_a, asset_b) for s in signals):
                    continue
            
            # 0.1 Entry Cutoff Check
            can_enter = True
            if self.entry_cutoff:
                if current_date.strftime("%H:%M") >= self.entry_cutoff:
                    can_enter = False
            
            try:
                # Use longer history for ADF and Hedge Ratio calculation to be stable
                # Using 2x lookback for calculation window if available, else lookback
                calc_window = min(len(df_a), self.lookback * 2)
                
                # We need OHLC for features, so take full DF slice
                window_a_df = df_a.iloc[-calc_window:]
                window_b_df = df_b.iloc[-calc_window:]
                
                # Defensive Fix: Ensure indices are tz-naive for alignment
                if window_a_df.index.tz is not None:
                    window_a_df = window_a_df.copy()
                    window_a_df.index = window_a_df.index.tz_localize(None)
                if window_b_df.index.tz is not None:
                    window_b_df = window_b_df.copy()
                    window_b_df.index = window_b_df.index.tz_localize(None)
                
                # For calc, we need series
                window_a = window_a_df['close']
                window_b = window_b_df['close']
                
                # Update Kalman Filter (Lagged - use previous beta for spread, then update)
                pair_key = (asset_a, asset_b)
                kf = self.kf_registry[pair_key]
                
                # Get the beta currently in the filter (from PREVIOUS bar)
                beta = kf.state 
                
                price_a = df_a.iloc[-1]['close']
                price_b = df_b.iloc[-1]['close']
                
                # Update the KF state for the NEXT bar IMMEDIATELY 
                # to avoid skipping it if we 'continue' later.
                current_time = current_date
                last_time = self.last_processed.get(pair_key)
                if last_time != current_time:
                    kf.update(price_a, price_b)
                    self.last_processed[pair_key] = current_time

                # 3. Calculate Spread and Z-Score using the LAGGED beta 
                # (to avoid identity Spread=0)
                # If beta is 0 (first bar), we'll skip this bar 
                # but the KF is now updated for next time.
                # Design Decision: We use the current dynamic beta applied to the lookback window.
                # This correctly measures how the *current* relationship stands relative to recent history.
                spread_series = window_a - beta * window_b
                
                # 3.1 Calculate Spread Indicators (RSI and ATR)
                spread_rsi = StaticIndicators.rsi(spread_series, period=self.rsi_period).iloc[-1]
                spread_atr = StaticIndicators.atr(
                    spread_series, spread_series, spread_series, # tr calculation handles high=low=close as same
                    period=14
                ).iloc[-1]
                
                mean_spread = spread_series.mean()
                std_spread = spread_series.std()
                
                if std_spread == 0: continue
                
                current_z = (spread_series.iloc[-1] - mean_spread) / std_spread
                
                # Check Stationarity (ADF Test)
                # We prioritize correctness over speed here to avoid false positives on non-stationary spreads.
                adf_stat = calculate_adf_statistic(spread_series)
                
                # 4. Market Intelligence for Bias Calculation
                sent_a = self.market_intel.get_sentiment(f"{asset_a} share news")
                sent_b = self.market_intel.get_sentiment(f"{asset_b} share news")
                # Bias = Influence of news on spread direction (A - beta*B)
                sentiment_bias = sent_a['score'] - sent_b['score']
                
                # Fit OU periodically or if not fitted. Use last 100 bars for stability.
                fit_window = min(len(spread_series), 100)
                ou = self.ou_registry[pair_key]
                
                if not self.ou_fitted[pair_key] or len(df_a) % 10 == 0:
                    ou_params = ou.fit(spread_series.iloc[-fit_window:].values)
                    if ou_params and ou_params.get('is_valid', False):
                        self.ou_fitted[pair_key] = True
                        self.ou_is_mr[pair_key] = ou_params.get('is_mr_regime', True)
                        if not self.ou_is_mr[pair_key]:
                            logger.info(f"⚠️ {asset_a}-{asset_b} skipped: Spread not mean-reverting (H={ou_params.get('hurst'):.2f})")
                    else:
                        self.ou_fitted[pair_key] = False
                        self.ou_is_mr[pair_key] = False
                
                # Check for regime block
                if not self.ou_is_mr[pair_key]:
                    continue
                    
                # Calculate current z and thresholds using sentiment bias
                if self.ou_fitted[pair_key]:
                    thresholds = ou.get_optimal_thresholds(confidence_level=0.90, sentiment_bias=sentiment_bias)
                    current_spread = spread_series.iloc[-1]
                    
                    if thresholds:
                        dynamic_entry_upper = thresholds['entry_upper']
                        dynamic_entry_lower = thresholds['entry_lower']
                        dynamic_exit_upper = thresholds['exit_upper']
                        dynamic_exit_lower = thresholds['exit_lower']
                        # For logging/UI, we still keep a z-score relative to the adjusted mean
                        current_z = (current_spread - thresholds['mu_adj']) / thresholds['eq_std'] if thresholds['eq_std'] > 0 else 0
                    else:
                        dynamic_entry_upper = mean_spread + (self.z_threshold * std_spread)
                        dynamic_entry_lower = mean_spread - (self.z_threshold * std_spread)
                        dynamic_exit_upper = mean_spread + (0.5 * std_spread)
                        dynamic_exit_lower = mean_spread - (0.5 * std_spread)
                else:
                    dynamic_entry_upper = mean_spread + (self.z_threshold * std_spread)
                    dynamic_entry_lower = mean_spread - (self.z_threshold * std_spread)
                    dynamic_exit_upper = mean_spread + (0.5 * std_spread)
                    dynamic_exit_lower = mean_spread - (0.5 * std_spread)
                    
                # 6. Entry Logic
                # Use a more lenient cointegration check for 5-minute data
                is_cointegrated = adf_stat < -1.4 
                should_skip = False # Rely on Hurst + OU Bands
                
                # AI Verification Removed (already using MI)
                # Decision logic
                is_over_upper = spread_series.iloc[-1] > dynamic_entry_upper
                is_under_lower = spread_series.iloc[-1] < dynamic_entry_lower
                
                if is_over_upper or is_under_lower:
                    logger.debug(f"Candidate: {asset_a}-{asset_b} Spread={spread_series.iloc[-1]:.4f} Range=[{dynamic_entry_lower:.4f}, {dynamic_entry_upper:.4f}] Coint={is_cointegrated}")
                         
                # Log State
                self.latest_state[pair_key] = {
                    'z_score': current_z,
                    'beta': beta,
                    'spread': spread_series.iloc[-1],
                    'rsi': spread_rsi,
                    'atr': spread_atr,
                    'timestamp': current_date,
                    'bias': sentiment_bias,
                    'dynamic_thresh_upper': dynamic_entry_upper,
                    'dynamic_thresh_lower': dynamic_entry_lower,
                    'hurst': getattr(ou, 'hurst_exponent', 0.5),
                    'adf': adf_stat
                }
                

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

                qty_a = self.risk_manager.calculate_size(capital, price_a, atr_a)
                
                # Ensure minimum viable quantity
                qty_a = max(1, qty_a)
                
                # Balance leg B
                qty_b = max(1, int(round(qty_a * beta)))

                # Generate Signals
                # Filter 1: Range Over-extension (RSI)
                # Filter 2: Regime Check (Hurst/ADF)
                can_short_spread = (is_over_upper and spread_rsi > self.rsi_entry_high)
                can_long_spread = (is_under_lower and spread_rsi < self.rsi_entry_low)
                
                if (can_short_spread or can_long_spread) and not should_skip and can_enter:
                    
                     # Market Intelligence Directional Scaling
                    sent_a = self.market_intel.get_sentiment(f"{asset_a} share news")
                    sent_b = self.market_intel.get_sentiment(f"{asset_b} share news")
                    
                    # Determine Directions
                    # High Z (> Thresh) -> Short A, Long B
                    # Low Z (< -Thresh) -> Long A, Short B
                    dir_a = -1 if current_z > 0 else 1
                    dir_b = 1 if current_z > 0 else -1
                    
                    mult_a = self._calculate_sentiment_impact(dir_a, sent_a['score'])
                    mult_b = self._calculate_sentiment_impact(dir_b, sent_b['score'])
                    
                    # Combined Multiplier (Conservative Average)
                    # If one leg opposes, we reduce the whole trade.
                    # If both agree, we boost.
                    # Logic: Min of both? Or Avg?
                    # Using Min ensures we don't boost if one leg is risky.
                    # boosting only if BOTH agree or one matches and other neutral.
                    
                    size_multiplier = min(mult_a, mult_b)
                    
                    # Logging specific reasoning
                    if size_multiplier != 1.0:
                        logger.info(f"📰 Sentiment Impact: {asset_a}({sent_a['score']:.2f}) {asset_b}({sent_b['score']:.2f}) -> Mult: {size_multiplier}x")

                    final_qty_a = max(1, int(qty_a * size_multiplier))
                    final_qty_b = max(1, int(qty_b * size_multiplier))
                    
                    # AI VALIDATION LAYER
                    features = self.ai_validator.extract_features(
                        spread_series, 
                        beta, 
                        spread_rsi, 
                        getattr(ou, 'hurst_exponent', 0.5), 
                        sentiment_bias
                    )
                    confidence = self.ai_validator.predict_confidence(features)
                    
                    if confidence < self.min_ai_confidence:
                        logger.info(f"🚫 AI Reject: {asset_a}-{asset_b} Confidence {confidence:.2f} < {self.min_ai_confidence}")
                        continue
                        
                    if current_z > 0:
                        signals.append(Signal(asset_a, SignalType.SELL, price_a, current_date, 
                                            quantity=final_qty_a, reason=f"Z={current_z:.2f} Sent={size_multiplier}x"))
                        signals.append(Signal(asset_b, SignalType.BUY, price_b, current_date, 
                                            quantity=final_qty_b, reason=f"Z={current_z:.2f} Sent={size_multiplier}x"))
                    else:
                        signals.append(Signal(asset_a, SignalType.BUY, price_a, current_date, 
                                            quantity=final_qty_a, reason=f"Z={current_z:.2f} Sent={size_multiplier}x"))
                        signals.append(Signal(asset_b, SignalType.SELL, price_b, current_date, 
                                            quantity=final_qty_b, reason=f"Z={current_z:.2f} Sent={size_multiplier}x"))
                    
                    # Record entry spread for stop loss
                    self.entry_spreads[pair_key] = spread_series.iloc[-1]
                
                # Exit Logic (Mean Reversion)
                # Exit when spread enters the exit band
                elif dynamic_exit_lower <= spread_series.iloc[-1] <= dynamic_exit_upper:
                     self._close_all_positions(asset_a, asset_b, current_date, df_a, df_b, signals, reason=f"OU Reversion (S={spread_series.iloc[-1]:.4f})")
                
                # Exit Logic (Hard ATR Stop Loss)
                else:
                    pos_a = self.positions.get(asset_a)
                    if pos_a and pos_a.quantity != 0:
                        is_short_spread = pos_a.quantity < 0 # qty_a < 0 means we sold spread (Short A, Long B)
                        entry_spread = self.entry_spreads.get(pair_key, spread_series.iloc[-1])
                        
                        # Spread move against us
                        move = spread_series.iloc[-1] - entry_spread
                        loss_dist = move if is_short_spread else -move
                        
                        if loss_dist > (self.atr_stop_mult * spread_atr):
                             logger.warning(f"🚨 Stop Loss Triggered: {asset_a}-{asset_b} Dist={loss_dist:.4f} Thresh={self.atr_stop_mult * spread_atr:.4f}")
                             self._close_all_positions(asset_a, asset_b, current_date, df_a, df_b, signals, reason="ATR Hard Stop")
                     
            except Exception as e:
                logger.error(f"Error processing pair {asset_a}-{asset_b}: {e}")
                continue
                
        return signals


    def _calculate_sentiment_impact(self, direction: int, score: float) -> float:
        """
        Calculate size multiplier based on sentiment and trade direction.
        Direction: 1 (Buy/Long), -1 (Sell/Short)
        Score: -1.0 to 1.0
        """
        # Alignment = direction * score
        # If > 0, they agree (Buy + Good News, Sell + Bad News)
        # If < 0, they disagree (Buy + Bad News, Sell + Good News)
        
        alignment = direction * score
        
        # Strong Agreement -> Boost
        if alignment > 0.3:
            return 1.25
            
        # Agreement -> Slight Boost/Normal
        if alignment > 0.1:
            return 1.1
            
        # Disagreement -> Reduce
        if alignment < -0.2:
            return 0.5
        
        # Strong Disagreement -> Block/Slash
        if alignment < -0.5:
            return 0.0 # No Trade
            
        return 1.0

    def _close_all_positions(self, asset_a: str, asset_b: str, current_date: datetime, df_a: pd.DataFrame, df_b: pd.DataFrame, signals: list, reason: str):
         for symbol, pos in [(asset_a, self.positions.get(asset_a)), 
                           (asset_b, self.positions.get(asset_b))]:
             if pos and pos.quantity != 0:
                 signal_type = SignalType.SELL if pos.quantity > 0 else SignalType.BUY
                 signals.append(Signal(symbol, signal_type, 
                                     df_a.iloc[-1]['close'] if symbol == asset_a else df_b.iloc[-1]['close'], 
                                     current_date, 
                                     quantity=abs(pos.quantity),
                                     reason=reason))

    def check_time_exit(self, current_time: datetime, asset_a: str, asset_b: str, signals: list, df_a: pd.Series, df_b: pd.Series):
        """
        Force exit if current time > time_stop
        """
        if not self.time_stop: return
        
        curr_str = current_time.strftime("%H:%M")
        if curr_str >= self.time_stop:
             # Square off
             for symbol, pos in [(asset_a, self.positions.get(asset_a)), 
                               (asset_b, self.positions.get(asset_b))]:
                 if pos and pos.quantity != 0:
                     signal_type = SignalType.SELL if pos.quantity > 0 else SignalType.BUY
                     signals.append(Signal(symbol, signal_type, 
                                          df_a.iloc[-1]['close'] if symbol == asset_a else df_b.iloc[-1]['close'], 
                                          current_time, 
                                          quantity=abs(pos.quantity),
                                          reason=f"Intraday Time Stop ({self.time_stop})"))
