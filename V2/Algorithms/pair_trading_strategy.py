from typing import Dict, List, Tuple
import pandas as pd
import numpy as np
from datetime import datetime
from .base_strategy import BaseStrategy
from Common import Signal, SignalType
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
                current_spread, current_z = self.calculate_spread_zscore(
                    df_a['close'], df_b['close']
                )
                
                if pd.isna(current_z):
                    continue
                
                price_a = df_a.iloc[-1]['close']
                price_b = df_b.iloc[-1]['close']
                
                # Entry Logic
                # Short Spread: Short A, Long B (Expect spread to decrease)
                if current_z > self.z_threshold:
                    # Signal to Short A
                    signals.append(Signal(
                        symbol=asset_a,
                        signal_type=SignalType.SELL,
                        price=price_a,
                        timestamp=current_date,
                        confidence=self.params['min_confidence'],
                        reason=f"Pair {asset_a}-{asset_b} Z-Score {current_z:.2f} > {self.z_threshold} (Short Spread)"
                    ))
                    # Signal to Long B
                    signals.append(Signal(
                        symbol=asset_b,
                        signal_type=SignalType.BUY,
                        price=price_b,
                        timestamp=current_date,
                        confidence=self.params['min_confidence'],
                        reason=f"Pair {asset_a}-{asset_b} Z-Score {current_z:.2f} > {self.z_threshold} (Short Spread)"
                    ))
                    
                # Long Spread: Long A, Short B (Expect spread to increase)
                elif current_z < -self.z_threshold:
                    # Signal to Long A
                    signals.append(Signal(
                        symbol=asset_a,
                        signal_type=SignalType.BUY,
                        price=price_a,
                        timestamp=current_date,
                        confidence=self.params['min_confidence'],
                        reason=f"Pair {asset_a}-{asset_b} Z-Score {current_z:.2f} < -{self.z_threshold} (Long Spread)"
                    ))
                    # Signal to Short B
                    signals.append(Signal(
                        symbol=asset_b,
                        signal_type=SignalType.SELL,
                        price=price_b,
                        timestamp=current_date,
                        confidence=self.params['min_confidence'],
                        reason=f"Pair {asset_a}-{asset_b} Z-Score {current_z:.2f} < -{self.z_threshold} (Long Spread)"
                    ))
                
                # Exit Logic (Mean Reversion or Stop Loss)
                # Note: The engine handles exits if we send opposite signals.
                # Ideally, we should check current position status, but here we just emit signals based on Z-Score.
                # The engine might need logic to close specific pairs, but standard BUY/SELL works if we just reverse.
                
                # If Z-Score is near zero (Mean Reversion Exit)
                elif abs(current_z) <= 0.5: # Close to mean (relaxed to 0.5 to ensure capture)
                     # Check if we have positions to close
                     if asset_a in self.positions:
                         pos_a = self.positions[asset_a]
                         # If Long A, Sell A
                         if pos_a.quantity > 0:
                             signals.append(Signal(
                                 symbol=asset_a, 
                                 signal_type=SignalType.SELL, 
                                 price=price_a, 
                                 timestamp=current_date, 
                                 reason=f"Pair {asset_a}-{asset_b} Mean Reversion (Z={current_z:.2f})"
                             ))
                         # If Short A, Buy A
                         elif pos_a.quantity < 0:
                             signals.append(Signal(
                                 symbol=asset_a, 
                                 signal_type=SignalType.BUY, 
                                 price=price_a, 
                                 timestamp=current_date, 
                                 reason=f"Pair {asset_a}-{asset_b} Mean Reversion (Z={current_z:.2f})"
                             ))
                     
                     if asset_b in self.positions:
                         pos_b = self.positions[asset_b]
                         # If Long B, Sell B
                         if pos_b.quantity > 0:
                             signals.append(Signal(
                                 symbol=asset_b, 
                                 signal_type=SignalType.SELL, 
                                 price=price_b, 
                                 timestamp=current_date, 
                                 reason=f"Pair {asset_a}-{asset_b} Mean Reversion (Z={current_z:.2f})"
                             ))
                         # If Short B, Buy B
                         elif pos_b.quantity < 0:
                             signals.append(Signal(
                                 symbol=asset_b, 
                                 signal_type=SignalType.BUY, 
                                 price=price_b, 
                                 timestamp=current_date, 
                                 reason=f"Pair {asset_a}-{asset_b} Mean Reversion (Z={current_z:.2f})"
                             ))
                     
            except Exception as e:
                logger.error(f"Error processing pair {asset_a}-{asset_b}: {e}")
                continue
                
        return signals
