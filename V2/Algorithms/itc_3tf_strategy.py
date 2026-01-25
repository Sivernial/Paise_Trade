import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime
import logging
from Algorithms.base_strategy import BaseStrategy
from Common import Signal, SignalType, Candle
from Common.quant_utils import calculate_vwap

logger = logging.getLogger(__name__)

class ITC3TFStrategy(BaseStrategy):
    """
    Phase 52: ITC 3-Timeframe MTFA.
    Uses 3-Layer Multi-Timeframe Analysis:
    - 1 Hour (The Sky): EMA 20 for Overall Market Direction
    - 30 Minutes (The Forest): EMA 9 for Confirmation Filter
    - 10 Minutes (The Trees): VWAP and EMA 9 for Precise Execution
    """
    
    def __init__(self, params: dict = None):
        super().__init__(params=params)
        self.params = params or {}
        self.symbol = self.params.get('symbol', 'ITC')
        self.sky_ema_period = self.params.get('sky_ema_period', 20)
        self.forest_ema_period = self.params.get('forest_ema_period', 9)
        self.tree_ema_period = self.params.get('tree_ema_period', 9)
        self.leverage = self.params.get('leverage', 4.0)
        
        # Safety Features
        self.profit_target_pct = self.params.get('profit_target', 0.015) # 1.5% for ITC
        self.stop_loss_pct = self.params.get('stop_loss', 0.005)        # 0.5% for ITC
        self.max_capital = self.params.get('max_capital')
        self.opening_noise_mins = self.params.get('opening_noise_mins', 5)
        self.allow_alignment_entry = self.params.get('allow_alignment_entry', True)
        
        self.trade_info = {}
        self.last_reset_date: Optional[datetime.date] = None

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

        forest_data = symbol_data.get('30minute')
        if forest_data is None:
            forest_data = symbol_data.get('30m')

        sky_data = symbol_data.get('1hour')
        if sky_data is None:
            sky_data = symbol_data.get('1h')

        if tree_data is None or forest_data is None or sky_data is None:
            return signals

        if len(tree_data) < 2 or len(forest_data) < self.forest_ema_period or len(sky_data) < self.sky_ema_period:
            return signals

        # 2. THE SKY (1H Trend Bias)
        ema_sky = sky_data['close'].ewm(span=self.sky_ema_period, adjust=False).mean()
        price = tree_data['close'].iloc[-1]
        last_sky_ema = ema_sky.iloc[-1]
        sky_bias = "BULLISH" if price > last_sky_ema else "BEARISH"

        # 3. THE FOREST (30m Confirmation)
        ema_forest = forest_data['close'].ewm(span=self.forest_ema_period, adjust=False).mean()
        last_forest_ema = ema_forest.iloc[-1]
        forest_bias = "BULLISH" if price > last_forest_ema else "BEARISH"

        # 4. THE TREES (10m Execution)
        ema_tree = tree_data['close'].ewm(span=self.tree_ema_period, adjust=False).mean()
        vwap = calculate_vwap(tree_data)
        
        prev_price = tree_data['close'].iloc[-2]
        curr_ema_tree = ema_tree.iloc[-1]
        prev_ema_tree = ema_tree.iloc[-2]
        curr_vwap = vwap.iloc[-1]
        
        # Strategy Status Logging
        logger.info(f"3TF MONITOR | {self.symbol} | Price: {price:.2f} | Sky: {sky_bias} | Forest: {forest_bias} | EMA9: {curr_ema_tree:.2f}")
        
        has_pos = self.symbol in (existing_positions or [])

        # 0. Noise Filter: Skip first X minutes of the day
        mins_since_open = (current_date.hour * 60 + current_date.minute) - (9 * 60 + 15)
        if mins_since_open < self.opening_noise_mins:
            return signals

        # 3. Entry Logic (Crossover + Alignment)
        if not has_pos:
            # First check of the day to allow alignment entry
            is_first_check_today = False
            if self.last_reset_date != current_date.date():
                self.last_reset_date = current_date.date()
                is_first_check_today = True

            # 3-WAY FILTER: All timeframes must align
            if sky_bias == forest_bias:
                if sky_bias == "BULLISH":
                    is_crossover = prev_price <= prev_ema_tree and price > curr_ema_tree
                    is_aligned = price >= curr_ema_tree and price >= curr_vwap
                    
                    if is_crossover or (self.allow_alignment_entry and is_first_check_today and is_aligned):
                        entry_type = "CROSSOVER" if is_crossover else "ALIGNMENT (GAP)"
                        reason = f"3TF BUY: {entry_type} | Sky+Forest BULL | Tree Xover @ {price:.2f}"
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
                
                elif sky_bias == "BEARISH":
                    is_crossdown = prev_price >= prev_ema_tree and price < curr_ema_tree
                    is_aligned = price <= curr_ema_tree and price <= curr_vwap
                    
                    if is_crossdown or (self.allow_alignment_entry and is_first_check_today and is_aligned):
                        entry_type = "CROSSOVER" if is_crossdown else "ALIGNMENT (GAP)"
                        reason = f"3TF SELL (SHORT): {entry_type} | Sky+Forest BEAR | Tree Xover @ {price:.2f}"
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
        
        # Use either passed capital or the defined cap
        effective_capital = min(capital, self.max_capital) if self.max_capital else capital
        
        total_buying_power = effective_capital * self.leverage
        return int(total_buying_power // price)
