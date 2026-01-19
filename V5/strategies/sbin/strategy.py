"""
SBIN Sentinel Strategy - Phase 40
Specialized momentum and pullback strategy for State Bank of India.

Entry Signals:
1. Open-Low Power Buy: Opens at day low (strong bullish demand)
2. Bullish Pullback: Price < VWAP but > EMA50 (dip in strong trend)

Exit Signals:
1. Profit Target: 1.0% gain
2. Stop Loss: 0.5% loss
3. End of Day: 15:15 IST square-off
"""
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List
import logging
import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from common.models import Signal, SignalType
from common.quant_utils import calculate_vwap, calculate_rsi, calculate_adx

logger = logging.getLogger(__name__)

class SbinSentinelStrategy:
    """
    SBIN-specific sentiment strategy combining FA bias with TA execution.
    """
    
    SYMBOL = "SBIN"
    
    def __init__(self, params: dict = None):
        self.params = params or {}
        self.lookback = self.params.get('lookback', 200)
        
        # Entry parameters
        self.rsi_period = self.params.get('rsi_period', 14)
        self.rsi_threshold = self.params.get('rsi_threshold', 45)  # Recovery signal
        self.ema_fast = self.params.get('ema_fast', 9)
        self.ema_trend = 50  # Long-term trend filter
        
        # Fundamental bias (can be updated externally)
        self.bias = self.params.get('bias', 'LONG')  # LONG, SHORT, or NEUTRAL
        
        # Trade tracking
        self.trade_info: Dict[str, dict] = {}
    
    def generate_signals(self, data: Dict[str, pd.DataFrame], 
                        current_date: datetime, 
                        capital: float = 100000,
                        existing_positions: List[str] = None) -> List[Signal]:
        """
        Generate trading signals for SBIN.
        
        Args:
            data: Dictionary with 'SBIN' as key and DataFrame with OHLCV data
            current_date: Current timestamp
            capital: Available capital
            existing_positions: List of symbols with open positions
            
        Returns:
            List of Signal objects
        """
        signals = []
        existing_positions = existing_positions or []
        
        if self.SYMBOL not in data:
            return signals
        
        df = data[self.SYMBOL].copy()
        if len(df) < max(self.lookback, self.ema_trend):
            return signals
        
        # Calculate indicators
        df['vwap'] = calculate_vwap(df)
        df['rsi'] = calculate_rsi(df['close'], self.rsi_period)
        df['ema_9'] = df['close'].ewm(span=self.ema_fast, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=self.ema_trend, adjust=False).mean()
        df['adx'] = calculate_adx(df)
        
        # Get intraday session data for Open-Low detection
        current_day_data = df[df.index.date == current_date.date()]
        if len(current_day_data) > 0:
            day_open = current_day_data['open'].iloc[0]
            day_low = current_day_data['low'].min()
            is_open_low = abs(day_open - day_low) < (day_open * 0.0005)  # 0.05% tolerance
        else:
            is_open_low = False
        
        # Current values
        price = df['close'].iloc[-1]
        vwap = df['vwap'].iloc[-1]
        rsi = df['rsi'].iloc[-1]
        ema_50 = df['ema_50'].iloc[-1]
        
        has_pos = self.SYMBOL in existing_positions
        
        # ========== ENTRY LOGIC ==========
        if not has_pos and self.bias == 'LONG':
            # Only trade before 2 PM (avoid end-of-day volatility)
            if current_date.hour < 14:
                
                # Scenario A: Open-Low Power Buy (Morning surge)
                if is_open_low and current_date.hour == 9 and current_date.minute < 45:
                    reason = "SENTINEL OHOL: Open=Low Bullish"
                    qty = self._calculate_quantity(capital, price)
                    signals.append(Signal(
                        symbol=self.SYMBOL,
                        signal_type=SignalType.BUY,
                        price=price,
                        timestamp=current_date,
                        quantity=qty,
                        reason=reason
                    ))
                    self.trade_info[self.SYMBOL] = {'entry_price': price, 'type': 'OHOL'}
                    return signals  # Early return for OHOL signal
                
                # Scenario B: Bullish Pullback (Dip buying in uptrend)
                is_pullback = price < vwap and price > ema_50
                is_recovery = rsi > self.rsi_threshold
                
                if is_pullback and is_recovery:
                    reason = f"SENTINEL DIP: P={price:.1f} < VWAP={vwap:.1f} (Trend Support)"
                    qty = self._calculate_quantity(capital, price)
                    signals.append(Signal(
                        symbol=self.SYMBOL,
                        signal_type=SignalType.BUY,
                        price=price,
                        timestamp=current_date,
                        quantity=qty,
                        reason=reason
                    ))
                    self.trade_info[self.SYMBOL] = {'entry_price': price, 'type': 'DIP'}
        
        # ========== EXIT LOGIC ==========
        elif has_pos:
            info = self.trade_info.get(self.SYMBOL, {'entry_price': price, 'type': 'DIP'})
            
            # Profit target (1.0% for focused trading)
            profit_target = price > info['entry_price'] * 1.01
            # Stop loss (0.5% - tight control)
            stop_loss = price < info['entry_price'] * 0.995
            # End of day exit
            eod_exit = current_date.hour == 15 and current_date.minute >= 15
            
            exit_triggered = False
            reason = ""
            
            if profit_target:
                exit_triggered, reason = True, "Profit Target (1.0%)"
            elif stop_loss:
                exit_triggered, reason = True, "Stop Loss (0.5%)"
            elif eod_exit:
                exit_triggered, reason = True, "End of Day"
            
            if exit_triggered:
                signals.append(Signal(
                    symbol=self.SYMBOL,
                    signal_type=SignalType.EXIT,
                    price=price,
                    timestamp=current_date,
                    reason=reason
                ))
                if self.SYMBOL in self.trade_info:
                    del self.trade_info[self.SYMBOL]
        
        return signals
    
    def _calculate_quantity(self, capital: float, price: float) -> int:
        """
        Calculate position size.
        Uses 50% of capital for focused trading on a single stock.
        """
        allocation = capital * 0.50
        if price <= 0:
            return 0
        return int(allocation / price)
