import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
import logging
from .base_strategy import BaseStrategy
from Common import Signal, SignalType
from Common.quant_utils import calculate_vwap, calculate_rsi, calculate_adx, calculate_atr

logger = logging.getLogger(__name__)

class SbinSentinelStrategy(BaseStrategy):
    """
    Phase 40: Single-Stock Sentinel (SBIN).
    Focuses on Trend Following and Momentum using VWAP, EMA, and RSI.
    """
    def __init__(self, params: dict = None):
        self.params = params or {}
        # We only care about SBIN
        self.symbol = "SBIN"
        self.lookback = self.params.get('lookback', 100)
        
        # Hyperparameters for Trend-Pulse
        self.rsi_period = self.params.get('rsi_period', 14)
        self.rsi_threshold = self.params.get('rsi_threshold', 55)
        self.ema_fast = self.params.get('ema_fast', 9)
        self.ema_slow = self.params.get('ema_slow', 21)
        
        # Fundamental Bias: Long Only for Jan 2026
        self.bias = self.params.get('bias', 'LONG') 
        
        self.trade_info: Dict[str, dict] = {}

    def generate_signals(self, data: Dict[str, pd.DataFrame], 
                        current_date: datetime, capital: float = 100000,
                        existing_positions: List[str] = None) -> List[Signal]:
        signals = []
        existing_positions = existing_positions or []
        
        if self.symbol not in data:
            return signals
            
        df = data[self.symbol].copy()
        if len(df) < max(self.lookback, self.ema_slow):
            return signals

        # 1. Calculate Indicators
        df['vwap'] = calculate_vwap(df)
        df['rsi'] = calculate_rsi(df['close'], self.rsi_period)
        df['ema_9'] = df['close'].ewm(span=self.ema_fast, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['adx'] = calculate_adx(df)
        
        # Day Open/Low for OHOL Strategy
        current_day_data = df[df.index.date == current_date.date()]
        day_open = current_day_data['open'].iloc[0]
        day_low = current_day_data['low'].min()
        is_open_low = abs(day_open - day_low) < (day_open * 0.0005) # 0.05% tolerance
        
        # Current Values
        price = df['close'].iloc[-1]
        vwap = df['vwap'].iloc[-1]
        rsi = df['rsi'].iloc[-1]
        ema_50 = df['ema_50'].iloc[-1]
        
        has_pos = self.symbol in existing_positions
        
        # 2. Entry Logic (Bullish Pullback)
        if not has_pos:
            # Only trade if we are in the morning/afternoon (Before 2 PM)
            if current_date.hour < 14:
                # LONG ONLY Bias
                # Scenario A: Open-Low Power Buy
                if is_open_low and current_date.hour == 9 and current_date.minute < 45:
                    reason = "SENTINEL OHOL: Open=Low Bullish"
                    qty = self._calculate_quantity(capital, price)
                    signals.append(Signal(symbol=self.symbol, signal_type=SignalType.BUY, price=price, timestamp=current_date, quantity=qty, reason=reason))
                    self.trade_info[self.symbol] = {'entry_price': price, 'type': 'OHOL'}
                    return signals

                # Scenario B: Bullish Pullback (Price < VWAP but Price > EMA 50)
                # Catching the dip in a strong trend
                is_pullback = price < vwap and price > ema_50
                is_recovery = rsi > 45 # Showing signs of snapping back
                
                if is_pullback and is_recovery:
                    reason = f"SENTINEL DIP: P={price:.1f} < VWAP={vwap:.1f} (Trend Support)"
                    qty = self._calculate_quantity(capital, price)
                    signals.append(Signal(symbol=self.symbol, signal_type=SignalType.BUY, price=price, timestamp=current_date, quantity=qty, reason=reason))
                    self.trade_info[self.symbol] = {'entry_price': price, 'type': 'DIP'}

        # 3. Exit Logic
        else:
            info = self.trade_info.get(self.symbol, {'entry_price': price, 'type': 'DIP'})
            
            # Profit Target (1.0% for single stock focus)
            profit_target = price > info['entry_price'] * 1.01
            # Stop Loss (0.5% tighter for focused trading)
            stop_loss = price < info['entry_price'] * 0.995
            
            exit_triggered = False
            reason = ""
            
            if profit_target:
                exit_triggered, reason = True, "Profit Target (1.0%)"
            elif stop_loss:
                exit_triggered, reason = True, "Stop Loss (0.5%)"
            elif current_date.hour == 15 and current_date.minute >= 15:
                exit_triggered, reason = True, "End of Day"
                
            if exit_triggered:
                signals.append(Signal(symbol=self.symbol, signal_type=SignalType.EXIT, price=price, timestamp=current_date, reason=reason))
                if self.symbol in self.trade_info: del self.trade_info[self.symbol]
                
        return signals

    def _calculate_quantity(self, capital: float, price: float) -> int:
        """Concentrated Sizing for Single Stock (50% of capital)"""
        # Since we are focused on 1 stock, we use higher leverage/sizing
        allocation = capital * 0.50
        if price <= 0: return 0
        return int(allocation / price)
