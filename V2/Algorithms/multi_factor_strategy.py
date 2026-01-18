import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from collections import deque
import logging
from .base_strategy import BaseStrategy
from Common import Signal, SignalType
from Common.quant_utils import calculate_pca_residuals, MarketRegimeDetector, calculate_hurst, calculate_half_life, calculate_adx, calculate_atr
from Common.microstructure import calculate_buying_pressure

logger = logging.getLogger(__name__)

class MultiFactorStrategy(BaseStrategy):
    """
    V3 Multi-Factor Statistical Arbitrage Strategy.
    Uses PCA to extract residuals from an asset basket and trades the reversion.
    """
    def __init__(self, params: dict = None):
        self.params = params or {}
        self.baskets = self.params.get('baskets', {
            'Banking': ['SBIN', 'PNB', 'BANKBARODA', 'CANBK', 'IDFCFIRSTB']
        })
        self.z_threshold = self.params.get('z_threshold', 2.0)
        self.exit_z_threshold = self.params.get('exit_z_threshold', 1.0) # Greedier profit booking
        self.n_components = self.params.get('n_components', 1)
        self.lookback = params.get('lookback', 180) # More responsive lookback
        self.last_metrics: List[dict] = [] # Storage for performance harvesting
        self.hurst_history: Dict[str, deque] = {} # Per-symbol Hurst history
        self.history_len = 50 # How many candles to use for median
        
        # Trade State Tracking (Stateful within the session)
        self.trade_info: Dict[str, dict] = {} 
        
        self.regime_detector = MarketRegimeDetector(n_regimes=2)
        
    def generate_signals(self, data: Dict[str, pd.DataFrame], 
                        current_date: datetime, capital: float = 100000,
                        existing_positions: List[str] = None) -> List[Signal]:
        signals = []
        self.last_metrics = [] # Reset for this cycle
        existing_positions = existing_positions or []
        
        for basket_name, symbols in self.baskets.items():
            basket_df = self._prepare_basket_data(data, symbols, cols=['close'])
            if basket_df.empty or len(basket_df) < self.lookback:
                continue
            
            # Prepare OHLC for indicators
            ohlc_data = {sym: data[sym] for sym in symbols if sym in data}
                
            log_returns = np.log(basket_df / basket_df.shift(1)).dropna()
            
            # 2. PCA Residual Extraction
            residuals = calculate_pca_residuals(log_returns.tail(self.lookback), n_components=self.n_components)
            cum_residuals = residuals.cumsum()
            
            # 3. Analyze each asset
            # Priority: Symbol Override > Basket Tier > Default
            symbol_overrides = self.params.get('symbol_thresholds', {})
            tiered_thresholds = self.params.get('tiered_thresholds', {})
            
            for symbol in symbols:
                if symbol not in cum_residuals.columns: continue
                
                # Dynamic Threshold Selection
                basket_threshold = symbol_overrides.get(symbol, 
                                    tiered_thresholds.get(basket_name, 
                                    self.z_threshold))
                
                # Define Price Early (Used for fallbacks)
                price = basket_df[symbol].iloc[-1]
                
                res_series = cum_residuals[symbol]
                
                # Z-Score
                mean_res = res_series.mean()
                std_res = res_series.std()
                current_res = res_series.iloc[-1]
                z_score = (current_res - mean_res) / std_res if std_res > 0 else 0
                
                # New Metrics for Research & Brain
                # Use actual OHLC if available for better ADX/ATR/Volume
                current_ohlc = ohlc_data.get(symbol)
                if current_ohlc is not None and not current_ohlc.empty:
                    current_ohlc = current_ohlc.iloc[~current_ohlc.index.duplicated(keep='last')]
                    atr_series = calculate_atr(current_ohlc.tail(100))
                    adx_series = calculate_adx(current_ohlc.tail(100))
                    bp_series = calculate_buying_pressure(current_ohlc.tail(100))
                    
                    # EMA for Trend Detection
                    closes = current_ohlc['close']
                    ema_50 = closes.ewm(span=50, adjust=False).mean().iloc[-1]
                    
                    current_atr = atr_series.iloc[-1] if not atr_series.empty else price * 0.01
                    current_adx = adx_series.iloc[-1] if not adx_series.empty else 0
                    current_bp = bp_series.iloc[-1] if not bp_series.empty else 0
                else:
                    current_atr = price * 0.01
                    current_adx = 0
                    current_bp = 0
                    ema_50 = price # Neutral fallback
                
                hurst = calculate_hurst(res_series.tail(100)) # Focus on recent memory
                h_life = calculate_half_life(res_series)
                
                # --- REGIME GATER (The Brain) ---
                # Self-Calibrating: Compare current Hurst to the stock's own median
                if symbol not in self.hurst_history:
                    self.hurst_history[symbol] = deque(maxlen=self.history_len)
                
                self.hurst_history[symbol].append(hurst)
                
                if len(self.hurst_history[symbol]) >= 10: # Wait for some history
                    h_median = np.median(self.hurst_history[symbol])
                else:
                    h_median = 0.5 # Fallback
                
                # REGIME CLASSIFICATION (The Brain)
                # 1. High Volatility / Trending
                is_trending_regime = (hurst > max(0.52, h_median + 0.02)) or (current_adx > 25)
                
                # 2. Reverting (High Fidelity) - RESTORED PHASE 35 LOGIC
                # Requires Hurst to be LOW (not just 'not high') and Volume to be low.
                is_reverting = hurst < min(0.48, h_median - 0.02) and current_adx < 25 and abs(current_bp) < 1.0
                
                # 2. Calm / Mean Reverting
                is_calm_regime = not is_trending_regime
                
                # Diagnostic Log
                if is_trending_regime and abs(z_score) > 1.5:
                    logger.debug(f"BRAIN: {symbol} is Trending (H={hurst:.2f}, ADX={current_adx:.1f}). Blocking Reversion.")
                
                # V3 BASELINE REVERSION LOGIC (With Momentum Filter)
                # price defined at top (line 70)
                has_pos = symbol in existing_positions
                
                # 1. Entry Logic (Only if no position)
                if not has_pos:
                    
                    
                    # MODE: GATED MEAN REVERSION (High Conviction)
                    # Only enter when the Brain says the market is actively reverting.
                    if is_reverting:
                        # Entrance: Aggressive but Gated
                        entry_threshold = max(1.5, basket_threshold - 0.25)
                        
                        if z_score > entry_threshold:
                            reason = f"REV SELL Z={z_score:.2f} (Gated)"
                            signals.append(Signal(symbol=symbol, signal_type=SignalType.SELL, price=price, timestamp=current_date, quantity=self._calculate_quantity(capital, price), reason=reason))
                            self.trade_info[symbol] = {'type': 'REV', 'side': 'SELL', 'entry_price': price, 'entry_z': z_score}
                        elif z_score < -entry_threshold:
                            reason = f"REV BUY Z={z_score:.2f} (Gated)"
                            signals.append(Signal(symbol=symbol, signal_type=SignalType.BUY, price=price, timestamp=current_date, quantity=self._calculate_quantity(capital, price), reason=reason))
                            self.trade_info[symbol] = {'type': 'REV', 'side': 'BUY', 'entry_price': price, 'entry_z': z_score}
                
                # 2. Specialized Exit Logic
                else:
                    info = self.trade_info.get(symbol, {'type': 'UNKNOWN', 'side': 'NONE', 'entry_price': price})
                    
                    exit_triggered = False
                    exit_reason = ""
                    
                    # Hard Stop Loss (1.0% Price Move)
                    if info['side'] == 'BUY' and price < info['entry_price'] * 0.99:
                        exit_triggered, exit_reason = True, "Price Stop (1.0%)"
                    elif info['side'] == 'SELL' and price > info['entry_price'] * 1.01:
                        exit_triggered, exit_reason = True, "Price Stop (1.0%)"
                    
                    # Strategy Specific Exits
                    if not exit_triggered:
                        if info['type'] == 'REV':
                            # Mean Reversion Target
                            if abs(z_score) < self.exit_z_threshold:
                                exit_triggered, exit_reason = True, f"REV Target Z={z_score:.1f}"
                            # Reversion Failure (Stop Loss on Z)
                            elif abs(z_score) > max(4.0, basket_threshold + 1.5):
                                exit_triggered, exit_reason = True, f"REV Failure Z={z_score:.1f}"
                        
                        elif info['type'] == 'TREND':
                            # Trend Exhaustion (Wait for reversal in Z momentum)
                            if info['side'] == 'BUY' and z_score < 1.0:
                                exit_triggered, exit_reason = True, f"Trend Weak Z={z_score:.1f}"
                            elif info['side'] == 'SELL' and z_score > -1.0:
                                exit_triggered, exit_reason = True, f"Trend Weak Z={z_score:.1f}"
                            # Extreme Reverse Momentum
                            elif is_reverting:
                                exit_triggered, exit_reason = True, "Trend Flip (Hurst)"
                    
                    if exit_triggered:
                        signals.append(Signal(symbol=symbol, signal_type=SignalType.EXIT, price=price, timestamp=current_date, reason=exit_reason))
                        if symbol in self.trade_info: del self.trade_info[symbol]
                    
                # 3. Capture Performance Metrics for Harvesting
                self.last_metrics.append({
                    'symbol': symbol,
                    'basket': basket_name,
                    'z_score': z_score,
                    'price': price,
                    'residual': current_res,
                    'residual_std': std_res,
                    'threshold': basket_threshold,
                    'in_pos': has_pos,
                    'hurst': hurst,
                    'half_life': h_life,
                    'adx': current_adx,
                    'regime': 'TREND' if is_trending_regime else ('CALM' if is_calm_regime else 'NEUTRAL')
                })
                    
        return signals

    def _prepare_basket_data(self, data: Dict[str, pd.DataFrame], symbols: List[str], cols: List[str] = ['close']) -> pd.DataFrame:
        """Combine close prices into a single DataFrame and handle duplicate timestamps."""
        basket_data = {}
        for sym in symbols:
            if sym in data:
                # Deduplicate individual series first
                series = data[sym][cols[0]]
                basket_data[sym] = series[~series.index.duplicated(keep='last')]
        
        if not basket_data:
            return pd.DataFrame()

        df = pd.DataFrame(basket_data).dropna()
        # Final de-duplication on the combined dataframe
        df = df[~df.index.duplicated(keep='last')]
        
        if len(df.columns) < 2:
             return pd.DataFrame() 
        return df

    def _calculate_quantity(self, capital: float, price: float) -> int:
        """Original Fixed-Dollar position sizing."""
        # Increased to 30% of capital for better utilization (Phase 37)
        risk_per_trade = capital * 0.30 
        if price <= 0: return 0
        return int(risk_per_trade / price)
