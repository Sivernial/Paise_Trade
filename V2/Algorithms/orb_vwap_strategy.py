from typing import Dict, List
import pandas as pd
import numpy as np
from datetime import datetime, time
from .base_strategy import BaseStrategy
from Common import Signal, SignalType
import logging

logger = logging.getLogger(__name__)

class ORBVWAPStrategy(BaseStrategy):
    
    def __init__(self, params: dict = None):
        default_params = {
            'orb_minutes': 15,
            'rvol_threshold': 1.5,
            'vwap_distance_atr': 1.5,
            'stop_atr_mult': 0.6,
            'trail_atr_mult': 2.0,
            'gap_min': 0.5,
            'gap_max': 3.0,
            'atr_period': 14,
            'min_confidence': 0.7,
            'rvol_lookback': 20
        }
        if params:
            default_params.update(params)
        super().__init__(default_params)
    
    def compute_intraday_vwap(self, df: pd.DataFrame) -> pd.Series:
        """Compute VWAP for a single day"""
        pv = (df['close'] * df['volume']).cumsum()
        vv = df['volume'].cumsum().replace(0, np.nan)
        return pv / vv
    
    def compute_rvol(self, df: pd.DataFrame, lookback_days: int = 20) -> pd.Series:
        """
        Compute relative volume compared to same time of day over past N days
        """
        if len(df) < lookback_days:
            return pd.Series(1.0, index=df.index)
        
        try:
            tod = df.index.time
            grouped = df.groupby([df.index.date, tod])['volume'].sum().unstack(level=0)
            
            if grouped.empty or len(grouped.columns) < 2:
                return pd.Series(1.0, index=df.index)
            
            # Average volume by time of day over lookback period
            lookback_cols = min(lookback_days, len(grouped.columns))
            avg_vol_by_tod = grouped.iloc[:, -lookback_cols:].mean(axis=1)
            
            # Map back to dataframe
            rvol = pd.Series(index=df.index, dtype=float)
            for idx in df.index:
                current_vol = df.loc[idx, 'volume']
                avg_vol = avg_vol_by_tod.get(idx.time(), np.nan)
                if pd.notna(avg_vol) and avg_vol > 0:
                    rvol[idx] = current_vol / avg_vol
                else:
                    rvol[idx] = 1.0
            
            return rvol
        except Exception as e:
            logger.warning(f"RVOL calculation failed: {e}, returning 1.0")
            return pd.Series(1.0, index=df.index)
    
    def generate_signals(self, data: Dict[str, pd.DataFrame], 
                        current_date: datetime) -> List[Signal]:
        signals = []
        
        orb_minutes = self.params['orb_minutes']
        rvol_threshold = self.params['rvol_threshold']
        vwap_dist_atr = self.params['vwap_distance_atr']
        atr_period = self.params['atr_period']
        lookback_days = self.params['rvol_lookback']
        
        for symbol, df in data.items():
            if len(df) < atr_period + 1:
                continue
            
            df_copy = df.copy()
            
            # Compute VWAP per day
            vwap_series = []
            for date, group in df_copy.groupby(df_copy.index.date):
                daily_vwap = self.compute_intraday_vwap(group)
                vwap_series.append(daily_vwap)
            df_copy['vwap'] = pd.concat(vwap_series)
            
            # Compute RVOL
            df_copy['rvol'] = self.compute_rvol(df_copy, lookback_days)
            
            # Compute ATR
            atr = self.static_ind.atr(df_copy['high'], df_copy['low'], df_copy['close'], atr_period)
            df_copy['atr'] = atr
            
            # Get current day data
            current_day = current_date.date()
            day_data = df_copy[df_copy.index.date == current_day]
            
            if day_data.empty or len(day_data) < 5:
                continue
            
            # Define time windows
            market_open = time(9, 15)
            orb_end_time = time(9, 15 + orb_minutes)
            
            try:
                # Get opening range data
                orb_data = day_data.between_time(market_open, orb_end_time)
                if orb_data.empty:
                    continue
                
                orh = orb_data['high'].max()
                orl = orb_data['low'].min()
                
                # Current bar
                current_bar = day_data.iloc[-1]
                current_time = current_bar.name.time()
                
                # Only trade after ORB period
                if current_time <= orb_end_time:
                    continue
                
                current_price = current_bar['close']
                current_vwap = current_bar['vwap']
                current_rvol = current_bar['rvol']
                current_atr = current_bar['atr']
                
                if pd.isna(current_vwap) or pd.isna(current_atr) or current_atr == 0:
                    continue
                
                vwap_distance = abs(current_price - current_vwap)
                
                # LONG signal: Break above ORH
                if (current_price > orh and 
                    current_price > current_vwap and 
                    current_rvol > rvol_threshold and 
                    vwap_distance < vwap_dist_atr * current_atr):
                    
                    signals.append(Signal(
                        symbol=symbol,
                        signal_type=SignalType.BUY,
                        price=current_price,
                        timestamp=current_date,
                        confidence=0.75,
                        reason=f"ORB Long: Price {current_price:.2f} > ORH {orh:.2f}, VWAP {current_vwap:.2f}, RVOL {current_rvol:.2f}"
                    ))
                
                # SHORT signal: Break below ORL
                elif (current_price < orl and 
                      current_price < current_vwap and 
                      current_rvol > rvol_threshold and 
                      vwap_distance < vwap_dist_atr * current_atr):
                    
                    signals.append(Signal(
                        symbol=symbol,
                        signal_type=SignalType.SELL,
                        price=current_price,
                        timestamp=current_date,
                        confidence=0.75,
                        reason=f"ORB Short: Price {current_price:.2f} < ORL {orl:.2f}, VWAP {current_vwap:.2f}, RVOL {current_rvol:.2f}"
                    ))
            
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                continue
        
        return signals
