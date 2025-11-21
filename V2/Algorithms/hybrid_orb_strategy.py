from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from datetime import datetime, time
from .base_strategy import BaseStrategy
from .orb_vwap_strategy import ORBVWAPStrategy
from .vwap_reversion_strategy import VWAPReversionStrategy
from Common import Signal, SignalType
import logging

logger = logging.getLogger(__name__)

class HybridORBStrategy(BaseStrategy):
    """
    Hybrid strategy that coordinates between ORB/VWAP Momentum and VWAP Mean Reversion
    Uses existing strategies and adds full position management (stops, targets, trailing)
    """
    
    def __init__(self, params: dict = None):
        default_params = {
            # ORB Parameters
            'orb_minutes': 15,
            'orb_start_time': '09:15',
            'entry_start_time': '09:30',
            'time_stop': '15:20',
            
            # Entry Filters
            'rvol_threshold': 1.5,
            'vwap_distance_atr': 1.5,
            
            # Risk Management
            'atr_period': 5,
            'stop_orb_atr_mult': 0.6,
            'stop_vwap_atr_mult': 1.0,
            'trail_atr_mult': 2.0,
            
            # Position Management
            'partial_exit_r': 1.0,
            'partial_exit_pct': 0.5,
            'use_chandelier_trail': True,
            
            # Market Filter
            'use_market_filter': True,
            'market_index': 'NIFTY 50',
            'ema_period': 20,
            
            # Mode Control
            'enable_longs': True,
            'enable_shorts': False,
            'enable_reversion': False,
            
            # RVOL
            'rvol_lookback': 20
        }
        if params:
            default_params.update(params)
        super().__init__(default_params)
        
        # Initialize sub-strategies
        orb_params = {
            'orb_minutes': self.params['orb_minutes'],
            'rvol_threshold': self.params['rvol_threshold'],
            'vwap_distance_atr': self.params['vwap_distance_atr'],
            'atr_period': self.params['atr_period'],
            'rvol_lookback': self.params['rvol_lookback']
        }
        self.orb_strategy = ORBVWAPStrategy(orb_params)
        
        reversion_params = {
            'rvol_threshold': self.params['rvol_threshold'] + 0.5,  # Higher threshold for reversion
            'atr_period': self.params['atr_period'],
            'rvol_lookback': self.params['rvol_lookback']
        }
        self.reversion_strategy = VWAPReversionStrategy(reversion_params)
    
    def check_market_filter(self, market_data: Optional[pd.DataFrame], 
                           current_date: datetime) -> bool:
        """Check if market (NIFTY) is above 20-EMA or VWAP"""
        if not self.params['use_market_filter']:
            return True
        
        if market_data is None or market_data.empty:
            logger.warning("No market data available for filter, allowing trade")
            return True
        
        try:
            current_day = current_date.date()
            day_data = market_data[market_data.index.date == current_day]
            
            if day_data.empty:
                return True
            
            current_bar = day_data.iloc[-1]
            current_price = current_bar['close']
            
            # Check VWAP
            vwap = self.static_ind.vwap(day_data['high'], day_data['low'], 
                                       day_data['close'], day_data['volume'])
            current_vwap = vwap.iloc[-1]
            
            # Check 20-EMA
            ema_20 = self.static_ind.ema(market_data['close'], self.params['ema_period'])
            current_ema = ema_20.iloc[-1]
            
            return current_price > current_vwap or current_price > current_ema
            
        except Exception as e:
            logger.error(f"Market filter check failed: {e}")
            return True
    
    def enhance_signal_with_position_management(self, signal: Signal, 
                                                orh: float, orl: float,
                                                vwap: float, atr: float,
                                                vwap_std: float = None) -> Signal:
        """Add stop loss, target, and trailing stop to signal"""
        if signal is None:
            return None
        
        is_long = signal.signal_type == SignalType.BUY
        price = signal.price
        
        if is_long:
            # Stop: max(ORH - 0.6*ATR, VWAP - 1.0*ATR)
            stop_option_1 = orh - (self.params['stop_orb_atr_mult'] * atr)
            stop_option_2 = vwap - (self.params['stop_vwap_atr_mult'] * atr)
            signal.stop_loss = max(stop_option_1, stop_option_2)
            
            # Risk and target
            risk = price - signal.stop_loss
            if risk > 0:
                signal.target = price + risk  # +1R
                signal.breakeven_trigger = signal.target
                signal.partial_exit_trigger = signal.target
            
            # Trailing stop
            if self.params['use_chandelier_trail']:
                signal.trailing_stop = price - (self.params['trail_atr_mult'] * atr)
            elif vwap_std:
                signal.trailing_stop = vwap - vwap_std
            else:
                signal.trailing_stop = price - (self.params['trail_atr_mult'] * atr)
        
        else:  # Short
            # Stop: min(ORL + 0.6*ATR, VWAP + 1.0*ATR)
            stop_option_1 = orl + (self.params['stop_orb_atr_mult'] * atr)
            stop_option_2 = vwap + (self.params['stop_vwap_atr_mult'] * atr)
            signal.stop_loss = min(stop_option_1, stop_option_2)
            
            risk = signal.stop_loss - price
            if risk > 0:
                signal.target = price - risk  # +1R
                signal.breakeven_trigger = signal.target
                signal.partial_exit_trigger = signal.target
            
            # Trailing stop
            if self.params['use_chandelier_trail']:
                signal.trailing_stop = price + (self.params['trail_atr_mult'] * atr)
            elif vwap_std:
                signal.trailing_stop = vwap + vwap_std
            else:
                signal.trailing_stop = price + (self.params['trail_atr_mult'] * atr)
        
        return signal
    
    def generate_signals(self, data: Dict[str, pd.DataFrame], 
                        current_date: datetime) -> List[Signal]:
        signals = []
        
        # Time windows
        entry_start = time(9, 30)
        time_stop = time(15, 20)
        current_time = current_date.time()
        
        # Check trading window
        if current_time < entry_start or current_time >= time_stop:
            return signals
        
        # Check market filter
        market_data = data.get(self.params['market_index'])
        if not self.check_market_filter(market_data, current_date):
            return signals
        
        # Generate signals from appropriate strategy
        if self.params['enable_longs'] or self.params['enable_shorts']:
            # Use ORB/VWAP Momentum strategy
            orb_signals = self.orb_strategy.generate_signals(data, current_date)
            
            for signal in orb_signals:
                # Filter by long/short preference
                if signal.signal_type == SignalType.BUY and not self.params['enable_longs']:
                    continue
                if signal.signal_type == SignalType.SELL and not self.params['enable_shorts']:
                    continue
                
                # Get necessary data for position management
                symbol = signal.symbol
                if symbol in data:
                    df = data[symbol]
                    current_day = current_date.date()
                    day_data = df[df.index.date == current_day]
                    
                    if not day_data.empty:
                        # Get ORB levels
                        market_open = time(9, 15)
                        orb_end = time(9, 15 + self.params['orb_minutes'])
                        orb_data = day_data.between_time(market_open, orb_end)
                        
                        if not orb_data.empty:
                            orh = orb_data['high'].max()
                            orl = orb_data['low'].min()
                            
                            # Get VWAP and ATR
                            vwap = self.static_ind.vwap(day_data['high'], day_data['low'],
                                                       day_data['close'], day_data['volume'])
                            atr = self.static_ind.atr(day_data['high'], day_data['low'],
                                                     day_data['close'], self.params['atr_period'])
                            
                            if not vwap.empty and not atr.empty:
                                current_vwap = vwap.iloc[-1]
                                current_atr = atr.iloc[-1]
                                
                                # Enhance signal with position management
                                enhanced_signal = self.enhance_signal_with_position_management(
                                    signal, orh, orl, current_vwap, current_atr
                                )
                                signals.append(enhanced_signal)
        
        # Add reversion signals if enabled
        if self.params['enable_reversion']:
            reversion_signals = self.reversion_strategy.generate_signals(data, current_date)
            # Add position management to reversion signals too
            for signal in reversion_signals:
                symbol = signal.symbol
                if symbol in data:
                    df = data[symbol]
                    current_day = current_date.date()
                    day_data = df[df.index.date == current_day]
                    
                    if not day_data.empty:
                        # For reversion, use VWAP-based stops
                        vwap = self.static_ind.vwap(day_data['high'], day_data['low'],
                                                   day_data['close'], day_data['volume'])
                        atr = self.static_ind.atr(day_data['high'], day_data['low'],
                                                 day_data['close'], self.params['atr_period'])
                        
                        if not vwap.empty and not atr.empty:
                            current_vwap = vwap.iloc[-1]
                            current_atr = atr.iloc[-1]
                            
                            # Use VWAP ± 2*ATR as ORH/ORL proxy for reversion
                            orh = current_vwap + (2 * current_atr)
                            orl = current_vwap - (2 * current_atr)
                            
                            enhanced_signal = self.enhance_signal_with_position_management(
                                signal, orh, orl, current_vwap, current_atr
                            )
                            signals.append(enhanced_signal)
        
        return signals
