import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime
import logging
from Algorithms.base_strategy import BaseStrategy
from Common import Signal, SignalType, Candle
from Common.quant_utils import calculate_vwap, round_to_tick

logger = logging.getLogger(__name__)

class Generic3TFStrategy(BaseStrategy):
    """
    Generic 3-Timeframe MTFA Strategy.
    - 1 Hour (The Sky): Macro trend filter.
    - 30 Minutes (The Forest): Confirmation filter.
    - 10 Minutes (The Trees): Execution triggers.
    """
    
    def __init__(self, params: dict = None):
        super().__init__(params=params)
        self.params = params or {}
        self.symbol = self.params.get('symbol', 'UNKNOWN')
        self.sky_ema_period = self.params.get('sky_ema_period', 20)
        self.forest_ema_period = self.params.get('forest_ema_period', 9)
        self.tree_ema_period = self.params.get('tree_ema_period', 9)
        self.leverage = self.params.get('leverage', 4.0)
        self.forced_direction = self.params.get('DIRECTION')
        
        self.profit_target_pct = self.params.get('profit_target', 0.015)
        self.stop_loss_pct = self.params.get('stop_loss', 0.005)
        self.max_capital = self.params.get('max_capital')
        self.tick_size = self.params.get('tick_size', 0.05)
        self.opening_noise_mins = self.params.get('opening_noise_mins', 5)
        self.allow_alignment_entry = self.params.get('allow_alignment_entry', True)
        
        self.use_atr_target = self.params.get('use_atr_target', True)
        self.atr_multiplier = self.params.get('atr_multiplier', 2.0)
        self.use_atr_sl = self.params.get('use_atr_sl', True)
        self.atr_sl_multiplier = self.params.get('atr_sl_multiplier', 1.5)
        self.adx_min = self.params.get('adx_min', 25)
        self.max_atr_allowed = self.params.get('max_atr_allowed', 0.05)
        
        # PROFT TAKING & EXITS
        self.partial_exit_atr = self.params.get('partial_exit_atr', 1.0) # Exit 50% at 1.0x ATR
        self.partial_exit_pct = self.params.get('partial_exit_pct') # V8 Explicit target
        self.partial_qty_pct = self.params.get('partial_qty_pct', 0.5) 
        
        self.trailing_timeframe = self.params.get('trailing_timeframe', 'tree')
        self.trailing_type = self.params.get('trailing_type', 'ema') 
        self.chandelier_multiplier = self.params.get('chandelier_multiplier', 2.0)
        self.max_ema_dist_atr = self.params.get('max_ema_dist_atr', 1.5)
        self.mean_reversion_pct = self.params.get('mean_reversion_pct')
        self.cool_down_mins = self.params.get('cool_down_mins', 30)
        
        # ADVANCED FEATURES (V8)
        self.gap_tolerance_pct = self.params.get('gap_tolerance_pct', 0.005) # 0.5% Gap
        self.use_market_depth = self.params.get('use_market_depth', True)
        self.correlated_index = self.params.get('correlated_index') # e.g. 'NIFTY', 'BANKNIFTY'
        
        # Volume Profile (Value Area) - Phase 4
        self.volume_profile = self.params.get('volume_profile', {'vah': None, 'val': None, 'poc': None})
        
        self.last_exit_time: Optional[datetime] = None
        self.trade_info = {}
        self.last_reset_date: Optional[datetime.date] = None

    def generate_signals(self, data: Dict[str, Dict[str, pd.DataFrame]], 
                        current_date: datetime, capital: float = 50000,
                        existing_positions: List[str] = None,
                        tick_data: Dict[str, Dict] = None,
                        indices_bias: Dict[str, str] = None,
                        volume_profile: Dict[str, float] = None) -> List[Signal]:
        signals = []
        
        # 1. Extract Data
        symbol_data = data.get(self.symbol)
        if not symbol_data: return signals

        tree_data = symbol_data.get('tree')
        if tree_data is None: tree_data = symbol_data.get('10minute')
        if tree_data is None: tree_data = symbol_data.get('10m')

        forest_data = symbol_data.get('30minute')
        if forest_data is None: forest_data = symbol_data.get('30m')

        sky_data = symbol_data.get('1hour')
        if sky_data is None: sky_data = symbol_data.get('1h')
        if sky_data is None: sky_data = symbol_data.get('60minute')

        if tree_data is None or forest_data is None or sky_data is None: return signals
        if len(tree_data) < 20 or len(forest_data) < self.forest_ema_period or len(sky_data) < self.sky_ema_period:
            return signals

        # 2. Indicators
        price = float(tree_data['close'].values[-1])
        
        # Use LIVE TICK PRICE if avail (more accurate for depth/gap checks, entry/exit levels, and stops)
        market_depth = None
        if tick_data and self.symbol in tick_data:
            tick = tick_data[self.symbol]
            price = tick.get('last_price', price)
            market_depth = tick.get('depth')
        
        ema_sky = sky_data['close'].ewm(span=self.sky_ema_period, adjust=False).mean()
        last_sky_ema = ema_sky.iloc[-1]
        sky_bias = "BULLISH" if price > last_sky_ema else "BEARISH"

        ema_forest = forest_data['close'].ewm(span=self.forest_ema_period, adjust=False).mean()
        last_forest_ema = ema_forest.iloc[-1]
        forest_bias = "BULLISH" if price > last_forest_ema else "BEARISH"

        ema_tree = tree_data['close'].ewm(span=self.tree_ema_period, adjust=False).mean()
        vwap = calculate_vwap(tree_data)
        
        prev_price = float(tree_data['close'].iloc[-2])
        curr_ema_tree = float(ema_tree.iloc[-1])
        prev_ema_tree = float(ema_tree.iloc[-2])
        curr_vwap = float(vwap.iloc[-1])
        
        # ATR & ADX Calculation (Robust V6 Implementation)
        tr = pd.concat([
            tree_data['high'] - tree_data['low'],
            (tree_data['high'] - tree_data['close'].shift(1)).abs(),
            (tree_data['low'] - tree_data['close'].shift(1)).abs()
        ], axis=1).max(axis=1)
        atr_series = tr.rolling(14).mean()
        atr = float(atr_series.iloc[-1])
        atr_pct = atr / price

        # ADX Calculation
        up = tree_data['high'] - tree_data['high'].shift(1)
        down = tree_data['low'].shift(1) - tree_data['low']
        plus_dm = np.where((up > down) & (up > 0), up, 0)
        minus_dm = np.where((down > up) & (down > 0), down, 0)
        
        tr_smooth = tr.rolling(14).mean().replace(0, 0.001)
        plus_di = 100 * (pd.Series(plus_dm, index=tree_data.index).rolling(14).mean() / tr_smooth)
        minus_di = 100 * (pd.Series(minus_dm, index=tree_data.index).rolling(14).mean() / tr_smooth)
        
        # Handle cases where plus_di + minus_di is zero
        denom = (plus_di + minus_di).replace(0, 0.001)
        dx = 100 * (abs(plus_di - minus_di) / denom)
        adx_series = dx.rolling(14).mean().fillna(0)
        adx = float(adx_series.iloc[-1])
        
        # Strategy Status Logging
        logger.info(f"3TF MONITOR | {self.symbol} | Price: {price:.2f} | Sky: {sky_bias} | Forest: {forest_bias} | ADX: {adx:.1f} | ATR%: {atr_pct*100:.2f}%")
        
        has_pos = self.symbol in (existing_positions or [])

        # 0. Noise Filter: Skip first X minutes of the day
        mins_since_open = (current_date.hour * 60 + current_date.minute) - (9 * 60 + 15)
        if mins_since_open < self.opening_noise_mins:
            return signals

        # 3. Entry Logic
        if not has_pos:
            is_first_check_today = False
            if self.last_reset_date != current_date.date():
                self.last_reset_date = current_date.date()
                # Alignment is ONLY allowed near market open (9:15 - 9:45) OR if allowed all day
                # This prevents "restart amnesia" buys midday
                alignment_window = self.params.get('alignment_window_mins', 30)
                if 0 <= mins_since_open <= alignment_window:
                    is_first_check_today = True
                else:
                    is_first_check_today = False

            # V8 GAP LOGIC (Optimized)
            is_gap_play = False
            conviction = "NORMAL"
            today_str = current_date.strftime("%Y-%m-%d")
            today_candles = tree_data[tree_data.index.astype(str).str.startswith(today_str)]
            
            if mins_since_open < 45 and not today_candles.empty:
                open_price = float(today_candles.iloc[0]['open'])
                prev_day_candles = tree_data[tree_data.index < today_candles.index[0]]
                prev_close = float(prev_day_candles.iloc[-1]['close']) if not prev_day_candles.empty else open_price
                
                if prev_close > 0:
                    gap_pct = (open_price - prev_close) / prev_close
                    if abs(gap_pct) > self.gap_tolerance_pct: 
                        if (gap_pct > 0 and sky_bias == "BULLISH") or (gap_pct < 0 and sky_bias == "BEARISH"):
                            is_gap_play = True
                            
                            # V8.2: VOLUME PROFILE CONVICTION
                            vp = volume_profile or self.volume_profile
                            vah, val = vp.get('vah'), vp.get('val')
                            
                            conviction = "NORMAL"
                            if vah and val:
                                if gap_pct > 0 and open_price > vah:
                                    conviction = "HIGH (Value Area Breakout)"
                                elif gap_pct < 0 and open_price < val:
                                    conviction = "HIGH (Value Area Breakout)"
                                elif val < open_price < vah:
                                    conviction = "LOW (Inside Value Area)"
                                    # Maybe reduce size or be more strict? For now just log.
                            
                            logger.info(f"GAP PLAY DETECTED: {gap_pct*100:.2f}% Gap follows Trend | Conviction: {conviction}")

            # V8.1: INDEX FILTER CHECK
            curr_index_bias = "NEUTRAL"
            if indices_bias and self.correlated_index in indices_bias:
                curr_index_bias = indices_bias[self.correlated_index]
                logger.info(f"INDEX FILTER | Symbol: {self.symbol} | Index: {self.correlated_index} | Bias: {curr_index_bias}")

            if sky_bias == forest_bias:
                # Target Calculation
                if self.use_atr_target:
                    actual_tp_pct = (self.atr_multiplier * atr) / price
                else:
                    actual_tp_pct = self.profit_target_pct

                if sky_bias == "BULLISH":
                    if self.forced_direction and self.forced_direction != "LONG":
                        logger.info(f"DIRECTION FILTERED: Skipping BUY for {self.symbol} because forced direction is {self.forced_direction}.")
                        return signals

                    if curr_index_bias == "BEARISH":
                        logger.info(f"INDEX FILTERED: Skipping BUY for {self.symbol} because {self.correlated_index} is BEARISH.")
                        return signals

                    is_crossover = prev_price <= prev_ema_tree and price > curr_ema_tree
                    is_aligned = price >= curr_ema_tree and price >= curr_vwap
                    
                    # V6.4: Overextension Filter (Distance from EMA)
                    ema_dist = price - curr_ema_tree
                    is_overextended = ema_dist > (self.max_ema_dist_atr * atr)
                    if self.mean_reversion_pct and (ema_dist / price) > self.mean_reversion_pct:
                        is_overextended = True
                    
                    # Cool-down check
                    in_cool_down = False
                    if self.last_exit_time and (current_date - self.last_exit_time).total_seconds() < self.cool_down_mins * 60:
                        in_cool_down = True

                    # V8.3: Gap Play Trigger (Aggressive Entry for High Conviction Breakouts)
                    is_gap_trigger = is_gap_play and conviction.startswith("HIGH")
                
                    if (is_crossover or is_gap_trigger or (self.allow_alignment_entry and is_first_check_today and is_aligned)) and not in_cool_down:
                        # V6 Filters (with Gap Override)
                        if is_overextended and not is_gap_play:
                            logger.info(f"FILTERED: Price too far from EMA Support ({ema_dist:.2f} > {self.max_ema_dist_atr}x ATR) for {self.symbol}")
                            return signals
                        if adx < self.adx_min:
                            logger.info(f"FILTERED: ADX too low ({adx:.1f} < {self.adx_min}) for {self.symbol}")
                            return signals
                        if atr_pct > self.max_atr_allowed and not is_gap_play:
                            logger.info(f"FILTERED: ATR% too high ({atr_pct*100:.2f}% > {self.max_atr_allowed*100:.2f}%) for {self.symbol}")
                            return signals
                        
                        # V8 MARKET DEPTH CHECK
                        if self.use_market_depth and market_depth:
                            # Check for SELLERS (Ask Qty > 0)
                            total_ask_qty = sum([ask['quantity'] for ask in market_depth.get('sell', [])])
                            if total_ask_qty == 0:
                                logger.warning(f"DEPTH FILTER: Upper Circuit Limit Hit (No Sellers). Skipping BUY.")
                                return signals
                            
                            # Check Imbalance
                            total_bid_qty = sum([bid['quantity'] for bid in market_depth.get('buy', [])])
                            if total_bid_qty > total_ask_qty * 2.0:
                                logger.info(f"DEPTH BOOST: Strong Buying Pressure (Bid/Ask > 2.0). High confidence.")

                        entry_type = "CROSSOVER"
                        if is_gap_trigger: entry_type = "GAP BREAKOUT"
                        elif self.allow_alignment_entry and is_first_check_today: entry_type = "ALIGNMENT (OPEN)"
                        
                        reason = f"3TF BUY: {entry_type} | Sky+Forest BULL | Tree @ {price:.2f} | Conv: {conviction}"
                        qty = self._calculate_quantity(capital, price)
                        
                        if self.use_atr_sl:
                            sl_price = round_to_tick(price - (self.atr_sl_multiplier * atr), self.tick_size)
                        else:
                            sl_price = round_to_tick(price * (1 - self.stop_loss_pct), self.tick_size)
                            
                        tp_price = round_to_tick(price * (1 + actual_tp_pct), self.tick_size)
                        # V8 DYNAMIC EXITS: Dance with the market
                        if self.partial_exit_pct:
                            partial_exit_trigger = round_to_tick(price * (1 + self.partial_exit_pct), self.tick_size)
                        else:
                            partial_exit_trigger = round_to_tick(price + (self.partial_exit_atr * atr), self.tick_size)
                        be_trigger = partial_exit_trigger 

                        signals.append(Signal(
                            symbol=self.symbol,
                            signal_type=SignalType.BUY,
                            price=price,
                            timestamp=current_date,
                            quantity=qty,
                            reason=reason,
                            stop_loss=sl_price,
                            target=tp_price,
                            breakeven_trigger=be_trigger,
                            partial_exit_trigger=partial_exit_trigger
                        ))
                        self.trade_info[self.symbol] = {
                            'entry_price': price, 
                            'side': 'LONG',
                            'sl_price': sl_price,
                            'extreme_price': price # For Chandelier
                        }
                        logger.info(f"SIGNAL: {reason} | SL: {sl_price:.2f} | TP: {tp_price:.2f} | P-Exit: {partial_exit_trigger:.2f}")
                
                elif sky_bias == "BEARISH":
                    if self.forced_direction and self.forced_direction != "SHORT":
                        logger.info(f"DIRECTION FILTERED: Skipping SELL for {self.symbol} because forced direction is {self.forced_direction}.")
                        return signals

                    if curr_index_bias == "BULLISH":
                        logger.info(f"INDEX FILTERED: Skipping SHORT for {self.symbol} because {self.correlated_index} is BULLISH.")
                        return signals

                    is_crossdown = prev_price >= prev_ema_tree and price < curr_ema_tree
                    is_aligned = price <= curr_ema_tree and price <= curr_vwap
                    
                    # V6.4: Overextension Filter (Distance from EMA)
                    ema_dist = curr_ema_tree - price
                    is_overextended = ema_dist > (self.max_ema_dist_atr * atr)
                    if self.mean_reversion_pct and (ema_dist / price) > self.mean_reversion_pct:
                        is_overextended = True
                    
                    # Cool-down check
                    in_cool_down = False
                    if self.last_exit_time and (current_date - self.last_exit_time).total_seconds() < self.cool_down_mins * 60:
                        in_cool_down = True

                    if (is_crossdown or (self.allow_alignment_entry and is_first_check_today and is_aligned)) and not in_cool_down:
                        # V6 Filters (with Gap Override)
                        if is_overextended and not is_gap_play:
                            logger.info(f"FILTERED: Price too far from EMA Resistance ({ema_dist:.2f} > {self.max_ema_dist_atr}x ATR) for {self.symbol}")
                            return signals
                        if adx < self.adx_min:
                            logger.info(f"FILTERED: ADX too low ({adx:.1f} < {self.adx_min}) for {self.symbol}")
                            return signals
                        if atr_pct > self.max_atr_allowed and not is_gap_play:
                            logger.info(f"FILTERED: ATR% too high ({atr_pct*100:.2f}% > {self.max_atr_allowed*100:.2f}%) for {self.symbol}")
                            return signals

                        # V8 MARKET DEPTH CHECK
                        if self.use_market_depth and market_depth:
                            # Check for BUYERS (Bid Qty > 0)
                            total_bid_qty = sum([bid['quantity'] for bid in market_depth.get('buy', [])])
                            if total_bid_qty == 0:
                                logger.warning(f"DEPTH FILTER: Lower Circuit Limit Hit (No Buyers). Skipping SELL.")
                                return signals
                            
                            # Check Imbalance
                            total_ask_qty = sum([ask['quantity'] for ask in market_depth.get('sell', [])])
                            if total_ask_qty > total_bid_qty * 2.0:
                                logger.info(f"DEPTH BOOST: Strong Selling Pressure (Ask/Bid > 2.0). High confidence.")

                        entry_type = "CROSSDOWN" if is_crossdown else "ALIGNMENT (GAP)"
                        reason = f"3TF SELL (SHORT): {entry_type} | Sky+Forest BEAR | Tree Xover @ {price:.2f}"
                        qty = self._calculate_quantity(capital, price)
                        
                        if self.use_atr_sl:
                            sl_price = round_to_tick(price + (self.atr_sl_multiplier * atr), self.tick_size)
                        else:
                            sl_price = round_to_tick(price * (1 + self.stop_loss_pct), self.tick_size)
                            
                        tp_price = round_to_tick(price * (1 - actual_tp_pct), self.tick_size)
                        # V8 DYNAMIC EXITS: Dance with the market
                        if self.partial_exit_pct:
                            partial_exit_trigger = round_to_tick(price * (1 - self.partial_exit_pct), self.tick_size)
                        else:
                            partial_exit_trigger = round_to_tick(price - (self.partial_exit_atr * atr), self.tick_size)
                        be_trigger = partial_exit_trigger 

                        signals.append(Signal(
                            symbol=self.symbol,
                            signal_type=SignalType.SELL,
                            price=price,
                            timestamp=current_date,
                            quantity=qty,
                            reason=reason,
                            stop_loss=sl_price,
                            target=tp_price,
                            breakeven_trigger=be_trigger,
                            partial_exit_trigger=partial_exit_trigger
                        ))
                        self.trade_info[self.symbol] = {
                            'entry_price': price, 
                            'side': 'SHORT',
                            'sl_price': sl_price,
                            'extreme_price': price # For Chandelier
                        }
                        logger.info(f"SIGNAL: {reason} | SL: {sl_price:.2f} | TP: {tp_price:.2f} | P-Exit: {partial_exit_trigger:.2f}")

        # 4. Exit Logic
        else:
            entry_info = self.trade_info.get(self.symbol, {})
            side = entry_info.get('side')
            entry_price = entry_info.get('entry_price')
            if not side or not entry_price: return signals

            # Target Calculation
            if self.use_atr_target:
                actual_tp_pct = (self.atr_multiplier * atr) / entry_price
            else:
                actual_tp_pct = self.profit_target_pct

            exit_triggered, reason = False, ""

            # Trailing Logic selection
            if self.trailing_type == 'chandelier':
                # Chandelier: Extreme Price - (Mult * ATR)
                if side == 'LONG':
                    entry_info['extreme_price'] = max(entry_info.get('extreme_price', price), price)
                    trailing_exit_price = entry_info['extreme_price'] - (self.chandelier_multiplier * atr)
                    ema_exit = price < trailing_exit_price
                    trailing_reason = f"Chandelier Exit ({self.chandelier_multiplier}x ATR) @ {trailing_exit_price:.2f}"
                else:
                    entry_info['extreme_price'] = min(entry_info.get('extreme_price', price), price)
                    trailing_exit_price = entry_info['extreme_price'] + (self.chandelier_multiplier * atr)
                    ema_exit = price > trailing_exit_price
                    trailing_reason = f"Chandelier Exit ({self.chandelier_multiplier}x ATR) @ {trailing_exit_price:.2f}"
            else:
                # Standard EMA Trailing
                trailing_ema = curr_ema_tree if self.trailing_timeframe == 'tree' else last_forest_ema
                trailing_reason = "EMA9 Trailing" if self.trailing_timeframe == 'tree' else "EMA-Forest Trailing"
                ema_exit = price < trailing_ema if side == 'LONG' else price > trailing_ema

            if side == 'LONG':
                profit_target = price >= entry_price * (1 + actual_tp_pct)
                
                # V6.1: Use stored SL price if available
                initial_sl = entry_info.get('sl_price')
                if initial_sl:
                    stop_loss = price <= initial_sl
                else:
                    stop_loss = price <= entry_price * (1 - self.stop_loss_pct)
                
                if profit_target:
                    exit_triggered, reason = True, f"EXIT SELL: Profit Target @ {price:.2f}"
                elif stop_loss:
                    exit_triggered, reason = True, f"EXIT SELL: STOP LOSS @ {price:.2f}"
                elif ema_exit:
                    exit_triggered, reason = True, f"EXIT SELL: {trailing_reason}"
                    
                if exit_triggered:
                    signals.append(Signal(symbol=self.symbol, signal_type=SignalType.SELL, price=price, 
                                          timestamp=current_date, quantity=0, reason=reason))
                    self.trade_info.pop(self.symbol, None)
                    self.last_exit_time = current_date
            
            elif side == 'SHORT':
                profit_target = price <= entry_price * (1 - actual_tp_pct)
                
                # V6.1: Use stored SL price if available
                initial_sl = entry_info.get('sl_price')
                if initial_sl:
                    stop_loss = price >= initial_sl
                else:
                    stop_loss = price >= entry_price * (1 + self.stop_loss_pct)
                    
                if profit_target:
                    exit_triggered, reason = True, f"EXIT BUY: Profit Target @ {price:.2f}"
                elif stop_loss:
                    exit_triggered, reason = True, f"EXIT BUY: STOP LOSS @ {price:.2f}"
                elif ema_exit:
                    exit_triggered, reason = True, f"EXIT BUY: {trailing_reason}"
                    
                if exit_triggered:
                    signals.append(Signal(symbol=self.symbol, signal_type=SignalType.BUY, price=price, 
                                          timestamp=current_date, quantity=0, reason=reason))
                    self.trade_info.pop(self.symbol, None)
                    self.last_exit_time = current_date

        return signals

    def _calculate_quantity(self, capital: float, price: float) -> int:
        if price <= 0: return 0
        effective_capital = min(capital, self.max_capital) if self.max_capital else capital
        total_buying_power = effective_capital * self.leverage
        return int(total_buying_power // price)
