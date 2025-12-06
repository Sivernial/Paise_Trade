from typing import Dict, List, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
from .base_strategy import BaseStrategy
from Common.enums import SignalType
from Common import Signal
from Common.quant_utils import calculate_hedge_ratio, calculate_adf_statistic
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
                window_a = df_a['close'].iloc[-calc_window:]
                window_b = df_b['close'].iloc[-calc_window:]
                
                current_spread, current_z, hedge_ratio, adf_stat = self.calculate_dynamic_zscore(
                    window_a, window_b
                )
                
                if pd.isna(current_z):
                    continue
                    
                # Store hedge ratio context (optional for debugging)
                # print(f"Pair {asset_a}-{asset_b} | Beta: {hedge_ratio:.3f} | ADF: {adf_stat:.3f} | Z: {current_z:.2f}")

                price_a = df_a.iloc[-1]['close']
                price_b = df_b.iloc[-1]['close']
                
                # Check Cointegration (ADF critical value approx -2.57 for 10%, -2.86 for 5%)
                # Relaxed threshold for backtest signals
                is_cointegrated = adf_stat < -1.94 
                
                if not is_cointegrated:
                    # If not cointegrated, avoid entering new positions, but allow exits
                    pass
                
                # Sanity Check for Hedge Ratio (Assume positive correlation for Banks)
                if not (0.2 <= hedge_ratio <= 4.0):
                    # logger.warning(f"Unstable Beta {hedge_ratio:.2f} for {asset_a}-{asset_b}")
                    continue

                # Entry Logic
                # Short Spread: Short A, Long B (Weighted by hedge ratio)
                # But engine supports integer quantities. 
                # Simplification: Trade 1 unit of A and beta units of B? 
                # Or equal value adjusted by beta?
                # For engine simplicity: 
                # Qty A = 1 * BaseQty, Qty B = Beta * (Price A / Price B) * BaseQty matches value?
                # Actually, spread = A - beta*B. To hedge, if we Short 1 unit of A, we Long beta units of B.
                
                # Qty A = Base Qty (approx 5000 INR value / 1000 price = 5)
                base_qty = 5
                qty_a = base_qty 
                qty_b = max(1, int(round(base_qty * hedge_ratio)))

                if current_z > self.z_threshold and is_cointegrated:
                    # Signal to Short A
                    signals.append(Signal(
                        symbol=asset_a,
                        signal_type=SignalType.SELL,
                        price=price_a,
                        quantity=qty_a,
                        timestamp=current_date,
                        confidence=self.params['min_confidence'],
                        reason=f"Pair {asset_a}-{asset_b} Z-Score {current_z:.2f} > {self.z_threshold} (Short Spread, Beta={hedge_ratio:.2f})"
                    ))
                    # Signal to Long B
                    signals.append(Signal(
                        symbol=asset_b,
                        signal_type=SignalType.BUY,
                        price=price_b,
                        quantity=qty_b,
                        timestamp=current_date,
                        confidence=self.params['min_confidence'],
                        reason=f"Pair {asset_a}-{asset_b} Z-Score {current_z:.2f} > {self.z_threshold} (Short Spread, Beta={hedge_ratio:.2f})"
                    ))
                    
                # Long Spread: Long A, Short B
                elif current_z < -self.z_threshold and is_cointegrated:
                    # Signal to Long A
                    signals.append(Signal(
                        symbol=asset_a,
                        signal_type=SignalType.BUY,
                        price=price_a,
                        quantity=qty_a,
                        timestamp=current_date,
                        confidence=self.params['min_confidence'],
                        reason=f"Pair {asset_a}-{asset_b} Z-Score {current_z:.2f} < -{self.z_threshold} (Long Spread, Beta={hedge_ratio:.2f})"
                    ))
                    # Signal to Short B
                    signals.append(Signal(
                        symbol=asset_b,
                        signal_type=SignalType.SELL,
                        price=price_b,
                        quantity=qty_b,
                        timestamp=current_date,
                        confidence=self.params['min_confidence'],
                        reason=f"Pair {asset_a}-{asset_b} Z-Score {current_z:.2f} < -{self.z_threshold} (Long Spread, Beta={hedge_ratio:.2f})"
                    ))
                
                # Exit Logic (Mean Reversion) - Check if Z-score crossed zero
                elif abs(current_z) <= 0.5:
                     # Check if we have positions to close
                     if asset_a in self.positions:
                         pos_a = self.positions[asset_a]
                         if pos_a.quantity != 0:
                             signals.append(Signal(
                                 symbol=asset_a, 
                                 signal_type=SignalType.SELL if pos_a.quantity > 0 else SignalType.BUY, 
                                 price=price_a, 
                                 timestamp=current_date, 
                                 reason=f"Mean Reversion (Z={current_z:.2f})"
                             ))
                     
                     if asset_b in self.positions:
                         pos_b = self.positions[asset_b]
                         if pos_b.quantity != 0:
                             signals.append(Signal(
                                 symbol=asset_b, 
                                 signal_type=SignalType.SELL if pos_b.quantity > 0 else SignalType.BUY, 
                                 price=price_b, 
                                 timestamp=current_date, 
                                 reason=f"Mean Reversion (Z={current_z:.2f})"
                             ))
                     
            except Exception as e:
                logger.error(f"Error processing pair {asset_a}-{asset_b}: {e}")
                continue
                
        return signals
