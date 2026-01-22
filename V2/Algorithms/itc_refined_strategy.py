import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime
import logging
from Algorithms.base_strategy import BaseStrategy
from Common import Signal, SignalType, Candle
from Common.quant_utils import calculate_vwap

logger = logging.getLogger(__name__)

class ITCRefinedStrategy(BaseStrategy):
    """
    Refined Multi-Timeframe Analysis (MTFA) Strategy for ITC.
    - Forest (1H): EMA trend filter.
    - Trees (10m): EMA and VWAP for crossover/alignment triggers.
    - Specifically optimized for intraday performance with transition-based entries.
    """
    
    def __init__(self, params: dict = None):
        super().__init__(params=params)
        self.params = params or {}
        self.symbol = self.params.get('symbol', 'ITC')
        self.forest_ema_period = self.params.get('forest_ema_period', 20)
        self.tree_ema_period = self.params.get('tree_ema_period', 9)
        self.leverage = self.params.get('leverage', 4.0)
        
        # Safety Features
        self.profit_target_pct = self.params.get('profit_target', 0.015) # 1.5% for ITC
        self.stop_loss_pct = self.params.get('stop_loss', 0.005)        # 0.5% for ITC
        
        self.trade_info = {}

    def generate_signals(self, data: Dict[str, Dict[str, pd.DataFrame]], 
                        current_date: datetime, capital: float = 50000,
                        existing_positions: List[str] = None) -> List[Signal]:
        signals = []
        
        # 1. Extract Data
        symbol_data = data.get(self.symbol)
        if not symbol_data:
            return signals

        # Support both '10minute' and '10m' keys
        tree_data = symbol_data.get('10minute')
        if tree_data is None:
            tree_data = symbol_data.get('10m')

        forest_data = symbol_data.get('1hour')
        if forest_data is None:
            forest_data = symbol_data.get('1h')

        if tree_data is None or forest_data is None or len(tree_data) < 2 or len(forest_data) < self.forest_ema_period:
            return signals

        # 2. Indicators
        ema_forest = forest_data['close'].ewm(span=self.forest_ema_period, adjust=False).mean()
        forest_trend_val = ema_forest.iloc[-1]
        forest_price = forest_data['close'].iloc[-1]
        forest_bias = "BULLISH" if forest_price > forest_trend_val else "BEARISH"

        ema_tree = tree_data['close'].ewm(span=self.tree_ema_period, adjust=False).mean()
        vwap = calculate_vwap(tree_data)
        
        price = tree_data['close'].iloc[-1]
        prev_price = tree_data['close'].iloc[-2]
        curr_ema_tree = ema_tree.iloc[-1]
        prev_ema_tree = ema_tree.iloc[-2]
        curr_vwap = vwap.iloc[-1]
        
        has_pos = self.symbol in (existing_positions or [])

        # 3. Entry Logic (Crossover + Alignment)
        if not has_pos:
            if forest_bias == "BULLISH":
                is_crossover = prev_price <= prev_ema_tree and price > curr_ema_tree
                is_above_vwap = price > curr_vwap
                
                if is_crossover and is_above_vwap:
                    reason = f"BY BUY: Forest BULL | Tree Cross-Up EMA9 & Above VWAP @ {price:.2f}"
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
                is_crossdown = prev_price >= prev_ema_tree and price < curr_ema_tree
                is_below_vwap = price < curr_vwap
                
                if is_crossdown and is_below_vwap:
                    reason = f"BY SELL (SHORT): Forest BEAR | Tree Cross-Down EMA9 & Below VWAP @ {price:.2f}"
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
            entry_info = self.trade_info.get(self.symbol, {})
            side = entry_info.get('side')
            entry_price = entry_info.get('entry_price')
            if not side or not entry_price: return signals

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
                    self.trade_info.pop(self.symbol, None)
            
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
                    self.trade_info.pop(self.symbol, None)

        return signals

    def _calculate_quantity(self, capital: float, price: float) -> int:
        """Calculate quantity based on capital and leverage."""
        if price <= 0: return 0
        total_buying_power = capital * self.leverage
        return int(total_buying_power // price)
