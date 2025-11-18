"""
Adaptive Momentum Breakout Strategy

A sophisticated intraday trading strategy designed for robust performance
across varying market conditions with built-in adaptability.

Strategy Components:
1. VWAP (Volume Weighted Average Price) - Institutional benchmark
2. SuperTrend - Volatility-adaptive trend following
3. Volume Profile Analysis - Market structure identification
4. Dynamic RSI - Adaptive momentum oscillator
5. ATR-based Risk Management - Volatility-adjusted position sizing

Features:
- Adaptive to market volatility
- Multiple timeframe confirmation
- Volume-based validation
- Robust risk management
- High-frequency intraday focus
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

from strategies.base_strategy import BaseStrategy
from data_structures.strategy_dataclass import Signal
from data_structures.common import SignalType


class AdaptiveMomentumBreakoutStrategy(BaseStrategy):
    """
    Advanced intraday strategy combining multiple adaptive indicators
    
    Key Features:
    - VWAP-based institutional alignment
    - SuperTrend for volatility-adaptive trend following
    - Volume profile for market structure
    - Dynamic RSI with adaptive periods
    - ATR-based risk management
    """
    
    def __init__(self, kite=None, params: Dict[str, Any] = None):
        default_params = {
            # VWAP parameters
            'vwap_period': 20,
            'vwap_deviation_threshold': 0.003,  # 0.3% deviation
            
            # SuperTrend parameters
            'supertrend_period': 10,
            'supertrend_multiplier': 3.0,
            
            # Volume parameters
            'volume_ma_period': 20,
            'volume_spike_threshold': 1.5,  # 1.5x average volume
            'volume_profile_periods': 50,
            
            # Dynamic RSI parameters
            'rsi_base_period': 14,
            'rsi_adaptive_range': [7, 21],  # Dynamic period range
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            
            # Risk management
            'atr_period': 14,
            'atr_multiplier': 2.0,
            'max_risk_per_trade': 0.02,  # 2% per trade
            'min_confidence': 0.75,
            
            # Market condition filters
            'min_volatility_percentile': 20,  # Avoid very low volatility
            'max_volatility_percentile': 80,  # Avoid extreme volatility
            'trend_confirmation_periods': 3,
            
            # Timeframe considerations
            'market_open_buffer': 30,  # Minutes after market open
            'market_close_buffer': 30,  # Minutes before market close
            'lunch_time_start': '12:00',
            'lunch_time_end': '13:30'
        }
        default_params.update(params or {})
        super().__init__(kite, default_params)
        
        # Initialize logger for compatibility
        import logging
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Strategy state
        self.position_entry_time = {}
        self.recent_signals = {}
        self.market_volatility_state = 'normal'
        
    def generate_signals(self, data: Dict[str, pd.DataFrame], current_date: datetime) -> List[Signal]:
        signals = []
        
        for symbol, df in data.items():
            if len(df) < max(self.params['volume_profile_periods'], 50):
                continue
                
            try:
                # Skip if outside trading hours
                if not self._is_trading_time(current_date):
                    continue
                
                # Calculate all indicators
                indicators = self._calculate_indicators(symbol, df)
                
                if not indicators:
                    continue
                
                # Determine market volatility state
                volatility_state = self._assess_market_volatility(df)
                
                # Generate signal based on comprehensive analysis
                signal = self._generate_adaptive_signal(
                    symbol, df, current_date, indicators, volatility_state
                )
                
                if signal:
                    signals.append(signal)
                    
            except Exception as e:
                self.logger.warning(f"Error analyzing {symbol}: {e}")
                continue
        
        return signals
    
    def _calculate_indicators(self, symbol: str, df: pd.DataFrame) -> Dict:
        """Calculate all technical indicators with robust error handling"""
        indicators = {}
        
        try:
            if len(df) < self.params.get('min_data_points', 50):
                return {}

            # VWAP calculation
            indicators['vwap'] = self._calculate_vwap(df)
            
            # SuperTrend calculation
            indicators['supertrend'], indicators['supertrend_direction'] = self._calculate_supertrend(df)
            
            # Volume analysis
            indicators['volume_sma'] = df['volume'].rolling(window=self.params['volume_ma_period']).mean()
            indicators['volume_ratio'] = df['volume'] / indicators['volume_sma']
            
            # Dynamic RSI
            indicators['rsi'] = self._calculate_adaptive_rsi(df)
            indicators['adaptive_rsi'] = indicators['rsi']  # Alias for compatibility
            
            # VWAP deviation
            indicators['vwap_deviation'] = self._calculate_vwap_deviation(df, indicators['vwap'])
            
            # Volume Profile
            indicators['volume_profile'] = self._calculate_volume_profile(df)
            
            # ATR for risk management - add specific error handling
            try:
                atr_period = self.params.get('atr_period', 14)
                if len(df) >= atr_period:
                    atr_result = self.ta.atr(df['high'], df['low'], df['close'], atr_period)
                    if atr_result is not None and len(atr_result) > 0:
                        indicators['atr'] = atr_result
                    else:
                        indicators['atr'] = pd.Series([1.0] * len(df), index=df.index)
                else:
                    indicators['atr'] = pd.Series([1.0] * len(df), index=df.index)
            except Exception as atr_error:
                self.logger.warning(f"ATR calculation failed for {symbol}: {atr_error}")
                indicators['atr'] = pd.Series([1.0] * len(df), index=df.index)
            
            # Price momentum indicators
            indicators['price_momentum'] = self._calculate_price_momentum(df)
            
            # Market microstructure
            indicators['bid_ask_pressure'] = self._estimate_bid_ask_pressure(df)
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"Error calculating indicators for {symbol}: {e}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            return {}
    
    def _calculate_vwap(self, df: pd.DataFrame) -> pd.Series:
        """Calculate Volume Weighted Average Price"""
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        cumulative_tpv = (typical_price * df['volume']).cumsum()
        cumulative_volume = df['volume'].cumsum()
        
        # Avoid division by zero
        cumulative_volume = cumulative_volume.replace(0, np.nan)
        vwap = cumulative_tpv / cumulative_volume
        
        return vwap.ffill()
    
    def _calculate_vwap_deviation(self, df: pd.DataFrame, vwap: pd.Series) -> pd.Series:
        """Calculate percentage deviation from VWAP"""
        return (df['close'] - vwap) / vwap
    
    def _calculate_supertrend(self, df: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> Tuple[pd.Series, pd.Series]:
        """Calculate SuperTrend indicator with proper error handling"""
        try:
            if len(df) < period:
                # Return empty series if insufficient data
                empty_series = pd.Series(index=df.index, dtype=float)
                return empty_series, empty_series
            
            # Calculate ATR
            atr = self.ta.atr(df['high'], df['low'], df['close'], period)
            
            # Calculate basic bands
            hl2 = (df['high'] + df['low']) / 2
            basic_upper = hl2 + (multiplier * atr)
            basic_lower = hl2 - (multiplier * atr)
            
            # Initialize arrays for calculations
            final_upper = basic_upper.copy()
            final_lower = basic_lower.copy()
            supertrend = pd.Series(index=df.index, dtype=float)
            direction = pd.Series(index=df.index, dtype=int)
            
            # Process each row
            for i in range(len(df)):
                if i == 0:
                    # Initialize first values
                    direction.iloc[i] = 1
                    supertrend.iloc[i] = final_lower.iloc[i]
                    continue
                
                # Get current and previous values safely
                try:
                    curr_close = df['close'].iloc[i]
                    prev_close = df['close'].iloc[i-1]
                    
                    # Adjust final bands based on previous values
                    if (basic_upper.iloc[i] < final_upper.iloc[i-1] or 
                        prev_close > final_upper.iloc[i-1]):
                        final_upper.iloc[i] = basic_upper.iloc[i]
                    else:
                        final_upper.iloc[i] = final_upper.iloc[i-1]
                    
                    if (basic_lower.iloc[i] > final_lower.iloc[i-1] or 
                        prev_close < final_lower.iloc[i-1]):
                        final_lower.iloc[i] = basic_lower.iloc[i]
                    else:
                        final_lower.iloc[i] = final_lower.iloc[i-1]
                    
                    # Determine SuperTrend direction and value
                    prev_supertrend = supertrend.iloc[i-1]
                    
                    if curr_close <= prev_supertrend:
                        direction.iloc[i] = -1
                        supertrend.iloc[i] = final_upper.iloc[i]
                    elif curr_close >= prev_supertrend:
                        direction.iloc[i] = 1
                        supertrend.iloc[i] = final_lower.iloc[i]
                    else:
                        direction.iloc[i] = direction.iloc[i-1]
                        supertrend.iloc[i] = prev_supertrend
                        
                except (IndexError, KeyError) as e:
                    # Handle any indexing errors gracefully
                    self.logger.warning(f"SuperTrend calculation error at index {i}: {e}")
                    direction.iloc[i] = direction.iloc[i-1] if i > 0 else 1
                    supertrend.iloc[i] = supertrend.iloc[i-1] if i > 0 else final_lower.iloc[i]
            
            return supertrend, direction
            
        except Exception as e:
            self.logger.error(f"SuperTrend calculation failed: {e}")
            # Return empty series on error
            empty_series = pd.Series(index=df.index, dtype=float)
            return empty_series, empty_series
    
    def _calculate_volume_profile(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate volume profile for support/resistance levels"""
        periods = self.params['volume_profile_periods']
        recent_df = df.tail(periods)
        
        # Create price bins
        price_range = recent_df['high'].max() - recent_df['low'].min()
        num_bins = min(20, len(recent_df) // 2)
        
        if num_bins < 5:
            return {'poc': df['close'].iloc[-1], 'value_area_high': df['high'].iloc[-1], 'value_area_low': df['low'].iloc[-1]}
        
        bins = np.linspace(recent_df['low'].min(), recent_df['high'].max(), num_bins)
        
        # Calculate volume at each price level
        volume_at_price = {}
        for i in range(len(bins)-1):
            mask = (recent_df['low'] <= bins[i+1]) & (recent_df['high'] >= bins[i])
            volume_at_price[bins[i]] = recent_df.loc[mask, 'volume'].sum()
        
        # Find Point of Control (POC) - price with highest volume
        poc_price = max(volume_at_price.keys(), key=lambda x: volume_at_price[x])
        
        # Calculate Value Area (70% of volume)
        total_volume = sum(volume_at_price.values())
        target_volume = total_volume * 0.7
        
        # Find value area boundaries
        sorted_prices = sorted(volume_at_price.keys(), key=lambda x: volume_at_price[x], reverse=True)
        cumulative_volume = 0
        value_area_prices = []
        
        for price in sorted_prices:
            cumulative_volume += volume_at_price[price]
            value_area_prices.append(price)
            if cumulative_volume >= target_volume:
                break
        
        return {
            'poc': poc_price,
            'value_area_high': max(value_area_prices),
            'value_area_low': min(value_area_prices)
        }
    
    def _calculate_adaptive_rsi(self, df: pd.DataFrame) -> pd.Series:
        """Calculate RSI with adaptive period based on market volatility"""
        base_period = self.params['rsi_base_period']
        min_period, max_period = self.params['rsi_adaptive_range']
        
        # Calculate volatility to adjust RSI period
        returns = df['close'].pct_change()
        volatility = returns.rolling(window=20).std()
        volatility_percentile = volatility.rolling(window=50).rank(pct=True)
        
        # Adaptive period: higher volatility = shorter period (more responsive)
        adaptive_period = pd.Series(index=df.index, dtype=int)
        for i in range(len(df)):
            if pd.isna(volatility_percentile.iloc[i]):
                adaptive_period.iloc[i] = base_period
            else:
                vol_pct = volatility_percentile.iloc[i]
                # Higher volatility (higher percentile) = shorter period
                period = int(max_period - (vol_pct * (max_period - min_period)))
                adaptive_period.iloc[i] = max(min_period, min(max_period, period))
        
        # Calculate RSI with adaptive period
        rsi_values = pd.Series(index=df.index, dtype=float)
        for i in range(max_period, len(df)):
            try:
                period = int(adaptive_period.iloc[i])  # Ensure integer
                start_idx = max(0, int(i - period + 1))  # Ensure integer
                end_idx = int(i + 1)  # Ensure integer
                
                # Use integer-based indexing
                window_data = df['close'].iloc[start_idx:end_idx]
                
                if len(window_data) >= period:
                    try:
                        rsi_result = self.ta.rsi(window_data, period)
                        if rsi_result is not None and len(rsi_result) > 0:
                            # Use proper indexing to get the last value
                            rsi_val = rsi_result.iloc[-1] if hasattr(rsi_result, 'iloc') else rsi_result[-1]
                            rsi_values.iloc[i] = rsi_val
                    except Exception as e:
                        self.logger.warning(f"RSI calculation error at index {i}: {e}")
                        rsi_values.iloc[i] = 50.0  # Default neutral RSI
            except Exception as e:
                self.logger.warning(f"Index conversion error at {i}: {e}")
                rsi_values.iloc[i] = 50.0  # Default neutral RSI
        
        return rsi_values.fillna(50)  # Neutral RSI for missing values
    
    def _calculate_price_momentum(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate various momentum indicators"""
        close_prices = df['close']
        
        try:
            momentum_5 = 0
            momentum_10 = 0
            momentum_20 = 0
            
            if len(close_prices) > 5:
                momentum_5 = close_prices.iloc[-1] / close_prices.iloc[-6] - 1
            
            if len(close_prices) > 10:
                momentum_10 = close_prices.iloc[-1] / close_prices.iloc[-11] - 1
                
            if len(close_prices) > 20:
                momentum_20 = close_prices.iloc[-1] / close_prices.iloc[-21] - 1
            
            return {
                'momentum_5': momentum_5,
                'momentum_10': momentum_10,
                'momentum_20': momentum_20,
            }
        except Exception as e:
            self.logger.warning(f"Price momentum calculation error: {e}")
            return {
                'momentum_5': 0,
                'momentum_10': 0,
                'momentum_20': 0,
            }
    
    def _estimate_bid_ask_pressure(self, df: pd.DataFrame) -> float:
        """Estimate buying/selling pressure from OHLC data"""
        # Use close position within the range as proxy for pressure
        if len(df) < 5:
            return 0.5
        
        recent_df = df.tail(5)
        
        # Calculate where close is within the high-low range
        pressure_values = []
        for _, row in recent_df.iterrows():
            if row['high'] != row['low']:
                pressure = (row['close'] - row['low']) / (row['high'] - row['low'])
                pressure_values.append(pressure)
        
        return np.mean(pressure_values) if pressure_values else 0.5
    
    def _assess_market_volatility(self, df: pd.DataFrame) -> str:
        """Assess current market volatility state"""
        if len(df) < 50:
            return 'normal'
        
        # Calculate recent volatility
        returns = df['close'].pct_change()
        recent_vol = returns.tail(20).std()
        historical_vol = returns.tail(100).std()
        
        vol_ratio = recent_vol / historical_vol if historical_vol > 0 else 1
        
        if vol_ratio > 1.5:
            return 'high'
        elif vol_ratio < 0.7:
            return 'low'
        else:
            return 'normal'
    
    def _generate_adaptive_signal(self, symbol: str, df: pd.DataFrame, 
                                current_date: datetime, indicators: Dict, 
                                volatility_state: str) -> Optional[Signal]:
        """Generate trading signal based on comprehensive analysis"""
        
        current_price = df['close'].iloc[-1]
        
        # Extract indicator values
        vwap = indicators['vwap'].iloc[-1]
        vwap_deviation = indicators['vwap_deviation'].iloc[-1]
        supertrend = indicators['supertrend'].iloc[-1]
        supertrend_direction = indicators['supertrend_direction'].iloc[-1]
        volume_ratio = indicators['volume_ratio'].iloc[-1]
        adaptive_rsi = indicators['adaptive_rsi'].iloc[-1]
        atr = indicators['atr'].iloc[-1]
        volume_profile = indicators['volume_profile']
        price_momentum = indicators['price_momentum']
        bid_ask_pressure = indicators['bid_ask_pressure']
        
        # Signal scoring system
        bullish_score = 0
        bearish_score = 0
        signal_reasons = []
        
        # 1. VWAP Analysis (25% weight)
        if current_price > vwap and vwap_deviation > self.params['vwap_deviation_threshold']:
            bullish_score += 25
            signal_reasons.append(f"Above VWAP by {vwap_deviation:.1%}")
        elif current_price < vwap and vwap_deviation < -self.params['vwap_deviation_threshold']:
            bearish_score += 25
            signal_reasons.append(f"Below VWAP by {abs(vwap_deviation):.1%}")
        
        # 2. SuperTrend Analysis (25% weight)
        if supertrend_direction > 0 and current_price > supertrend:
            bullish_score += 25
            signal_reasons.append("SuperTrend bullish")
        elif supertrend_direction < 0 and current_price < supertrend:
            bearish_score += 25
            signal_reasons.append("SuperTrend bearish")
        
        # 3. Volume Analysis (20% weight)
        if volume_ratio > self.params['volume_spike_threshold']:
            volume_weight = 20
            if current_price > vwap:
                bullish_score += volume_weight
                signal_reasons.append(f"High volume support ({volume_ratio:.1f}x)")
            else:
                bearish_score += volume_weight
                signal_reasons.append(f"High volume breakdown ({volume_ratio:.1f}x)")
        
        # 4. RSI Analysis (15% weight)
        if adaptive_rsi < self.params['rsi_oversold'] and adaptive_rsi > 20:  # Not extremely oversold
            bullish_score += 15
            signal_reasons.append(f"RSI oversold ({adaptive_rsi:.1f})")
        elif adaptive_rsi > self.params['rsi_overbought'] and adaptive_rsi < 80:  # Not extremely overbought
            bearish_score += 15
            signal_reasons.append(f"RSI overbought ({adaptive_rsi:.1f})")
        
        # 5. Volume Profile Analysis (10% weight)
        poc_distance = abs(current_price - volume_profile['poc']) / current_price
        if poc_distance < 0.005:  # Within 0.5% of POC
            if current_price > volume_profile['poc']:
                bullish_score += 10
                signal_reasons.append("Above POC")
            else:
                bearish_score += 10
                signal_reasons.append("Below POC")
        
        # 6. Momentum Analysis (5% weight)
        if price_momentum['momentum_5'] > 0.002:  # 0.2% momentum
            bullish_score += 5
            signal_reasons.append("Positive momentum")
        elif price_momentum['momentum_5'] < -0.002:
            bearish_score += 5
            signal_reasons.append("Negative momentum")
        
        # Determine signal direction and confidence
        signal_type = None
        confidence = 0
        
        total_score = bullish_score + bearish_score
        if total_score > 0:
            if bullish_score > bearish_score:
                signal_type = SignalType.BUY
                confidence = bullish_score / 100
            else:
                signal_type = SignalType.SELL
                confidence = bearish_score / 100
        
        # Adjust confidence based on market conditions
        confidence = self._adjust_confidence_for_market_conditions(
            confidence, volatility_state, bid_ask_pressure
        )
        
        # Apply minimum confidence filter
        if confidence < self.params['min_confidence']:
            return None
        
        # Calculate stop loss and take profit
        if signal_type:
            stop_loss, take_profit = self._calculate_risk_levels(
                current_price, signal_type, atr
            )
            
            return Signal(
                symbol=symbol,
                signal_type=signal_type,
                confidence=confidence,
                price=current_price,
                timestamp=current_date,
                reason=f"Adaptive Momentum: {', '.join(signal_reasons[:3])}",
                indicators={
                    'vwap': vwap,
                    'supertrend': supertrend,
                    'adaptive_rsi': adaptive_rsi,
                    'volume_ratio': volume_ratio,
                    'atr': atr,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'volatility_state': volatility_state,
                    'confidence_breakdown': {
                        'bullish_score': bullish_score,
                        'bearish_score': bearish_score,
                        'total_possible': 100
                    }
                }
            )
        
        return None
    
    def _adjust_confidence_for_market_conditions(self, base_confidence: float, 
                                               volatility_state: str, 
                                               bid_ask_pressure: float) -> float:
        """Adjust confidence based on market conditions"""
        adjusted_confidence = base_confidence
        
        # Volatility adjustment
        if volatility_state == 'high':
            adjusted_confidence *= 0.9  # Reduce confidence in high volatility
        elif volatility_state == 'low':
            adjusted_confidence *= 0.95  # Slightly reduce in low volatility
        
        # Bid-ask pressure adjustment
        if 0.3 <= bid_ask_pressure <= 0.7:
            adjusted_confidence *= 1.05  # Boost for balanced pressure
        elif bid_ask_pressure < 0.2 or bid_ask_pressure > 0.8:
            adjusted_confidence *= 0.9  # Reduce for extreme pressure
        
        return min(0.95, adjusted_confidence)  # Cap at 95%
    
    def _calculate_risk_levels(self, price: float, signal_type: SignalType, 
                             atr: float) -> tuple:
        """Calculate stop loss and take profit levels"""
        atr_multiplier = self.params['atr_multiplier']
        
        if signal_type == SignalType.BUY:
            stop_loss = price - (atr * atr_multiplier)
            take_profit = price + (atr * atr_multiplier * 2)  # 2:1 RR ratio
        else:
            stop_loss = price + (atr * atr_multiplier)
            take_profit = price - (atr * atr_multiplier * 2)
        
        return stop_loss, take_profit
    
    def _is_trading_time(self, current_time: datetime) -> bool:
        """Check if current time is within trading hours"""
        current_hour = current_time.hour
        current_minute = current_time.minute
        
        # Market hours: 9:15 AM to 3:30 PM IST
        market_open = 9 * 60 + 15  # 9:15 AM in minutes
        market_close = 15 * 60 + 30  # 3:30 PM in minutes
        current_minutes = current_hour * 60 + current_minute
        
        # Add buffers
        effective_open = market_open + self.params['market_open_buffer']
        effective_close = market_close - self.params['market_close_buffer']
        
        # Lunch time filter
        lunch_start = 12 * 60  # 12:00 PM
        lunch_end = 13 * 60 + 30  # 1:30 PM
        
        # Check if within trading hours and not during lunch
        in_trading_hours = effective_open <= current_minutes <= effective_close
        not_lunch_time = not (lunch_start <= current_minutes <= lunch_end)
        
        return in_trading_hours and not_lunch_time