import pandas as pd
import numpy as np
from datetime import datetime, date
from typing import Dict, List, Optional
import logging
from .base_strategy import BaseStrategy
from Common import Signal, SignalType
from Common.quant_utils import calculate_vwap, calculate_rsi

logger = logging.getLogger(__name__)

class SilverSentinelStrategy(BaseStrategy):
    """
    Phase 41: Silver Sentinel (SILVERBEES).
    Uses Multi-Timeframe Analysis (MTFA):
    - 1 Hour (The Forest): EMA 20 for Trend Bias.
    - 10 Minutes (The Trees): VWAP and EMA 9 for Execution.
    
    Phase 46: Added Opening Noise Filter and Gap Alignment.
    """
    def __init__(self, params: dict = None):
        super().__init__(params=params)
        self.params = params or {}
        self.symbol = "SILVERBEES"
        
        # 1H (Forest) Parameters
        self.forest_ema_period = self.params.get('forest_ema', 20)
        
        # 10m (Trees) Parameters
        self.tree_ema_period = self.params.get('tree_ema', 9)
        self.rsi_period = self.params.get('rsi_period', 14)
        
        # Risk Management
        self.profit_target_pct = self.params.get('profit_target', 0.005) # 0.5%
        self.stop_loss_pct = self.params.get('stop_loss', 0.0025)       # 0.25%
        self.leverage = self.params.get('leverage', 4.0)
        
        # Gap & Noise Handling
        # Skip first 10 minutes (9:15-9:25) to avoid open noise as per user request
        self.opening_noise_mins = self.params.get('opening_noise_mins', 10)
        self.allow_alignment_entry = self.params.get('allow_alignment_entry', True)
        
        self.trade_info: Dict[str, dict] = {}
        self.last_reset_date: Optional[date] = None

    def generate_signals(self, data: Dict[str, Dict[str, pd.DataFrame]], 
                        current_date: datetime, capital: float = 100000,
                        existing_positions: List[str] = None) -> List[Signal]:
        """
        Generate signals based on dual-timeframe data.
        Expected data structure: { 'SILVERBEES': { '10m': df_10m, '1h': df_1h } }
        """
        signals = []
        existing_positions = existing_positions or []
        
        if self.symbol not in data:
            return signals
            
        dfs = data[self.symbol]
        # Support both '10m' and '10minute' / '1h' and '60minute'
        df_10m = dfs.get('10m')
        if df_10m is None:
            df_10m = dfs.get('10minute')
            
        df_1h = dfs.get('1h')
        if df_1h is None:
            df_1h = dfs.get('60minute')
        
        if df_10m is None or df_1h is None:
            logger.warning(f"Missing timeframe data for {self.symbol}")
            return signals
            
        df_10m = df_10m.copy()
        df_1h = df_1h.copy()
        
        if len(df_10m) < 2 or len(df_1h) < self.forest_ema_period:
            return signals

        # 1. THE FOREST (1H Trend Bias)
        df_1h['ema_forest'] = df_1h['close'].ewm(span=self.forest_ema_period, adjust=False).mean()
        last_1h_price = df_1h['close'].iloc[-1]
        last_forest_ema = df_1h['ema_forest'].iloc[-1]
        
        forest_bias = "BULLISH" if last_1h_price > last_forest_ema else "BEARISH"
        
        # 2. THE TREES (10m Execution)
        df_10m['vwap'] = calculate_vwap(df_10m)
        df_10m['ema_tree'] = df_10m['close'].ewm(span=self.tree_ema_period, adjust=False).mean()
        df_10m['rsi'] = calculate_rsi(df_10m['close'], self.rsi_period)
        
        price = df_10m['close'].iloc[-1]
        prev_price = df_10m['close'].iloc[-2]
        vwap = df_10m['vwap'].iloc[-1]
        curr_ema_tree = df_10m['ema_tree'].iloc[-1]
        prev_ema_tree = df_10m['ema_tree'].iloc[-2]
        
        has_pos = self.symbol in existing_positions

        # 0. Noise Filter: Skip first X minutes of the day
        # Calculate minutes since market open (Assuming 9:15 AM start)
        mins_since_open = (current_date.hour * 60 + current_date.minute) - (9 * 60 + 15)
        
        if mins_since_open < self.opening_noise_mins:
            return signals
        
        # 3. Entry Logic (Crossover + Alignment)
        if not has_pos:
            # Check if this is the first check of the day to allow alignment entry
            is_first_check_today = False
            curr_date_only = current_date.date()
            if self.last_reset_date != curr_date_only:
                self.last_reset_date = curr_date_only
                is_first_check_today = True

            if forest_bias == "BULLISH":
                # Entry: Price crosses above EMA 9 OR is already aligned at the start
                is_crossover = prev_price <= prev_ema_tree and price > curr_ema_tree
                is_aligned = price > curr_ema_tree and price > vwap
                
                if is_crossover or (self.allow_alignment_entry and is_first_check_today and is_aligned):
                    entry_type = "CROSSOVER" if is_crossover else "ALIGNMENT (GAP)"
                    reason = f"BY BUY: {entry_type} | Forest BULL | Tree Above EMA9 & VWAP @ {price:.2f}"
                    qty = self._calculate_quantity(capital, price)
                    
                    sl_price = price * (1 - self.stop_loss_pct)
                    tp_price = price * (1 + self.profit_target_pct)
                    
                    signals.append(Signal(
                        symbol=self.symbol,
                        signal_type=SignalType.BUY,
                        price=price,
                        timestamp=current_date,
                        quantity=qty,
                        reason=reason,
                        stop_loss=sl_price,
                        target=tp_price
                    ))
                    self.trade_info[self.symbol] = {'entry_price': price, 'side': 'LONG'}
                    logger.info(f"SIGNAL: {reason} | SL: {sl_price:.2f} | TP: {tp_price:.2f}")
                    
            elif forest_bias == "BEARISH":
                # Entry: Price crosses below EMA 9 OR is already aligned at the start
                is_crossdown = prev_price >= prev_ema_tree and price < curr_ema_tree
                is_aligned = price < curr_ema_tree and price < vwap
                
                if is_crossdown or (self.allow_alignment_entry and is_first_check_today and is_aligned):
                    entry_type = "CROSSOVER" if is_crossdown else "ALIGNMENT (GAP)"
                    reason = f"BY SELL (SHORT): {entry_type} | Forest BEAR | Tree Below EMA9 & VWAP @ {price:.2f}"
                    qty = self._calculate_quantity(capital, price)
                    
                    sl_price = price * (1 + self.stop_loss_pct)
                    tp_price = price * (1 - self.profit_target_pct)
                    
                    signals.append(Signal(
                        symbol=self.symbol,
                        signal_type=SignalType.SELL,
                        price=price,
                        timestamp=current_date,
                        quantity=qty,
                        reason=reason,
                        stop_loss=sl_price,
                        target=tp_price
                    ))
                    self.trade_info[self.symbol] = {'entry_price': price, 'side': 'SHORT'}
                    logger.info(f"SIGNAL: {reason} | SL: {sl_price:.2f} | TP: {tp_price:.2f}")

        # 4. Exit Logic
        else:
            info = self.trade_info.get(self.symbol)
            if not info: return signals
            
            entry_price = info['entry_price']
            side = info['side']
            
            exit_triggered = False
            reason = ""
            
            if side == 'LONG':
                profit_target = price > entry_price * (1 + self.profit_target_pct)
                stop_loss = price < entry_price * (1 - self.stop_loss_pct)
                ema_exit = price < curr_ema_tree
                
                if profit_target:
                    exit_triggered, reason = True, f"EXIT SELL: Profit Target Reached @ {price:.2f}"
                elif stop_loss:
                    exit_triggered, reason = True, f"EXIT SELL: STOP LOSS TRIGGERED @ {price:.2f}"
                elif ema_exit:
                    exit_triggered, reason = True, f"EXIT SELL: EMA9 Trailing Exit @ {price:.2f}"
                    
                if exit_triggered:
                    signals.append(Signal(
                        symbol=self.symbol,
                        signal_type=SignalType.SELL,
                        price=price,
                        timestamp=current_date,
                        quantity=0,
                        reason=reason
                    ))
            
            elif side == 'SHORT':
                profit_target = price < entry_price * (1 - self.profit_target_pct)
                stop_loss = price > entry_price * (1 + self.stop_loss_pct)
                ema_exit = price > curr_ema_tree
                
                if profit_target:
                    exit_triggered, reason = True, f"EXIT BUY (COVER): Profit Target Reached @ {price:.2f}"
                elif stop_loss:
                    exit_triggered, reason = True, f"EXIT BUY (COVER): STOP LOSS TRIGGERED @ {price:.2f}"
                elif ema_exit:
                    exit_triggered, reason = True, f"EXIT BUY (COVER): EMA9 Trailing Exit @ {price:.2f}"
                    
                if exit_triggered:
                    signals.append(Signal(
                        symbol=self.symbol,
                        signal_type=SignalType.BUY,
                        price=price,
                        timestamp=current_date,
                        quantity=0,
                        reason=reason
                    ))
            
            if exit_triggered:
                if self.symbol in self.trade_info:
                    del self.trade_info[self.symbol]
        
        return signals

    def _calculate_quantity(self, capital: float, price: float) -> int:
        """Calculate quantity based on capital and leverage."""
        if price <= 0: return 0
        total_buying_power = capital * self.leverage
        return int(total_buying_power // price)
