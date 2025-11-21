from typing import Dict, List
import pandas as pd
import numpy as np
from datetime import datetime, time
from .base_strategy import BaseStrategy
from Common import Signal, SignalType
import logging

logger = logging.getLogger(__name__)

class VWAPReversionStrategy(BaseStrategy):
    
    def __init__(self, params: dict = None):
        default_params = {
            'min_time': '10:00',
            'rvol_threshold': 2.0,
            'extension_atr_mult': 2.0,
            'vwap_reclaim_sd': 0.5,
            'atr_period': 14,
            'lookback_bars': 3,
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
    
    def compute_intraday_vwap_std(self, df: pd.DataFrame) -> pd.Series:
        """Compute VWAP standard deviation for a single day"""
        vwap = self.compute_intraday_vwap(df)
        squared_diff = ((df['close'] - vwap) ** 2 * df['volume']).cumsum()
        cum_vol = df['volume'].cumsum().replace(0, np.nan)
        variance = squared_diff / cum_vol
        return np.sqrt(variance)
    
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
    
    def detect_failed_push(self, df: pd.DataFrame, lookback: int = 3) -> tuple:
        """Detect failed upside or downside push"""
        if len(df) < lookback + 1:
            return False, False
        
        recent = df.iloc[-lookback:]
        
        # Failed upside: lower high
        failed_upside = False
        if len(recent) >= 2:
            highs = recent['high'].values
            if len(highs) >= 2 and highs[-1] < highs[-2]:
                failed_upside = True
        
        # Failed downside: higher low
        failed_downside = False
        if len(recent) >= 2:
            lows = recent['low'].values
            if len(lows) >= 2 and lows[-1] > lows[-2]:
                failed_downside = True
        
        return failed_upside, failed_downside
    
    def generate_signals(self, data: Dict[str, pd.DataFrame], 
                        current_date: datetime) -> List[Signal]:
        signals = []
        
        min_time_obj = time(10, 0)
        rvol_threshold = self.params['rvol_threshold']
        extension_atr = self.params['extension_atr_mult']
        vwap_reclaim = self.params['vwap_reclaim_sd']
        atr_period = self.params['atr_period']
        lookback = self.params['lookback_bars']
        lookback_days = self.params['rvol_lookback']
        
        for symbol, df in data.items():
            if len(df) < atr_period + lookback:
                continue
            
            try:
                df_copy = df.copy()
                
                # Compute VWAP per day
                vwap_series = []
                vwap_std_series = []
                for date, group in df_copy.groupby(df_copy.index.date):
                    daily_vwap = self.compute_intraday_vwap(group)
                    daily_vwap_std = self.compute_intraday_vwap_std(group)
                    vwap_series.append(daily_vwap)
                    vwap_std_series.append(daily_vwap_std)
                
                df_copy['vwap'] = pd.concat(vwap_series)
                df_copy['vwap_std'] = pd.concat(vwap_std_series)
                
                # Compute RVOL
                df_copy['rvol'] = self.compute_rvol(df_copy, lookback_days)
                
                # Compute ATR
                atr = self.static_ind.atr(df_copy['high'], df_copy['low'], df_copy['close'], atr_period)
                df_copy['atr'] = atr
                
                # Get current day data
                current_day = current_date.date()
                day_data = df_copy[df_copy.index.date == current_day]
                
                if day_data.empty or len(day_data) < lookback:
                    continue
                
                # Current bar
                current_bar = day_data.iloc[-1]
                current_time = current_bar.name.time()
                
                # Only trade after min_time
                if current_time < min_time_obj:
                    continue
                
                current_price = current_bar['close']
                current_vwap = current_bar['vwap']
                current_std = current_bar['vwap_std']
                current_rvol = current_bar['rvol']
                current_atr = current_bar['atr']
                
                if pd.isna(current_vwap) or pd.isna(current_std) or pd.isna(current_atr):
                    continue
                
                if current_std == 0 or current_atr == 0:
                    continue
                
                vwap_distance = abs(current_price - current_vwap)
                is_extended = vwap_distance > extension_atr * current_atr
                
                # Detect failed push using recent bars from current day
                failed_upside, failed_downside = self.detect_failed_push(day_data, lookback)
                
                upper_band = current_vwap + vwap_reclaim * current_std
                lower_band = current_vwap - vwap_reclaim * current_std
                
                # BUY: Oversold reversion
                if (current_rvol > rvol_threshold and 
                    is_extended and 
                    current_price < current_vwap and 
                    failed_downside and 
                    current_price > lower_band):
                    
                    signals.append(Signal(
                        symbol=symbol,
                        signal_type=SignalType.BUY,
                        price=current_price,
                        timestamp=current_date,
                        confidence=0.70,
                        reason=f"VWAP Reversion Long: Price {current_price:.2f} < VWAP {current_vwap:.2f}, RVOL {current_rvol:.2f}, Distance {vwap_distance:.2f}"
                    ))
                
                # SELL: Overbought reversion
                elif (current_rvol > rvol_threshold and 
                      is_extended and 
                      current_price > current_vwap and 
                      failed_upside and 
                      current_price < upper_band):
                    
                    signals.append(Signal(
                        symbol=symbol,
                        signal_type=SignalType.SELL,
                        price=current_price,
                        timestamp=current_date,
                        confidence=0.70,
                        reason=f"VWAP Reversion Short: Price {current_price:.2f} > VWAP {current_vwap:.2f}, RVOL {current_rvol:.2f}, Distance {vwap_distance:.2f}"
                    ))
            
            except Exception as e:
                logger.error(f"Error processing {symbol} in VWAP Reversion: {e}")
                continue
        
        return signals
