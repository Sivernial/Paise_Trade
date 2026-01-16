import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from collections import deque
import logging
from .base_strategy import BaseStrategy
from Common import Signal, SignalType
from Common.quant_utils import calculate_pca_residuals, MarketRegimeDetector, calculate_hurst, calculate_half_life, calculate_adx

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
        
        self.regime_detector = MarketRegimeDetector(n_regimes=2)
        
    def generate_signals(self, data: Dict[str, pd.DataFrame], 
                        current_date: datetime, capital: float = 100000,
                        existing_positions: List[str] = None) -> List[Signal]:
        signals = []
        self.last_metrics = [] # Reset for this cycle
        existing_positions = existing_positions or []
        
        for basket_name, symbols in self.baskets.items():
            basket_df = self._prepare_basket_data(data, symbols)
            if basket_df.empty or len(basket_df) < self.lookback:
                # logger.debug(f"Basket {basket_name} insufficient data: {len(basket_df)} bars")
                continue
                
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
                
                res_series = cum_residuals[symbol]
                
                # Z-Score
                mean_res = res_series.mean()
                std_res = res_series.std()
                current_res = res_series.iloc[-1]
                z_score = (current_res - mean_res) / std_res if std_res > 0 else 0
                
                # New Metrics for Research & Brain
                hurst = calculate_hurst(res_series.tail(100)) # Focus on recent memory
                h_life = calculate_half_life(res_series)
                adx_series = calculate_adx(basket_df[[symbol]].rename(columns={symbol: 'close'}).assign(high=basket_df[symbol], low=basket_df[symbol])) # Simple ADX on closes for now
                current_adx = adx_series.iloc[-1] if not adx_series.empty else 0
                
                # --- REGIME GATER (The Brain) ---
                # Self-Calibrating: Compare current Hurst to the stock's own median
                if symbol not in self.hurst_history:
                    self.hurst_history[symbol] = deque(maxlen=self.history_len)
                
                self.hurst_history[symbol].append(hurst)
                
                if len(self.hurst_history[symbol]) >= 10: # Wait for some history
                    h_median = np.median(self.hurst_history[symbol])
                else:
                    h_median = 0.5 # Fallback
                
                # Relative Gating
                is_trending = hurst > max(0.55, h_median + 0.05) or current_adx > 30
                is_reverting = hurst < min(0.45, h_median - 0.05) and current_adx < 25
                
                # Diagnostic Log (Reduced noise, only high-conviction flags)
                if is_trending and abs(z_score) > 1.5:
                    logger.debug(f"BRAIN: {symbol} is Trending (H={hurst:.2f}, ADX={current_adx:.1f}). Blocking Reversion.")
                
                # V3 BASELINE REVERSION LOGIC (With Momentum Filter)
                price = basket_df[symbol].iloc[-1]
                has_pos = symbol in existing_positions
                
                # 1. Entry Logic (Only if no position)
                if not has_pos:
                    # REVERSION ENTRY: Only if NOT trending
                    if is_reverting:
                        if z_score > basket_threshold:
                            signals.append(Signal(
                                symbol=symbol,
                                signal_type=SignalType.SELL,
                                price=price,
                                timestamp=current_date,
                                quantity=self._calculate_quantity(capital, price),
                                reason=f"PCA Z={z_score:.2f} (Rev Entry)"
                            ))
                        elif z_score < -basket_threshold:
                            signals.append(Signal(
                                symbol=symbol,
                                signal_type=SignalType.BUY,
                                price=price,
                                timestamp=current_date,
                                quantity=self._calculate_quantity(capital, price),
                                reason=f"PCA Z={z_score:.2f} (Rev Entry)"
                            ))
                            
                    # TREND ENTRY: If trending, go with the flow
                    elif is_trending:
                        # If Z is high and Hurst is high, it's a breakout
                        if z_score > 1.5: # Extreme positive momentum
                            signals.append(Signal(
                                symbol=symbol,
                                signal_type=SignalType.BUY, # Jump on the trend
                                price=price,
                                timestamp=current_date,
                                quantity=self._calculate_quantity(capital, price),
                                reason=f"MOMENTUM H={hurst:.2f} (Trend Entry)"
                            ))
                        elif z_score < -1.5: # Extreme negative momentum
                            signals.append(Signal(
                                symbol=symbol,
                                signal_type=SignalType.SELL, # Short the trend
                                price=price,
                                timestamp=current_date,
                                quantity=self._calculate_quantity(capital, price),
                                reason=f"MOMENTUM H={hurst:.2f} (Trend Entry)"
                            ))
                
                # 2. Exit Logic (Returning to Mean)
                else:
                    if abs(z_score) < self.exit_z_threshold:
                        # Determine exit type based on price/z-score would be ideal, 
                        # but signaling an 'EXIT' or just the opposite type works.
                        # PaperTrader handles SELL as 'close long' or 'open short'. 
                        # To be safe, we need to know the position direction.
                        # For now, let's assume we want to flatten.
                        signals.append(Signal(
                            symbol=symbol,
                            signal_type=SignalType.EXIT, # New SignalType or handle in trader
                            price=price,
                            timestamp=current_date,
                            reason=f"PCA Z={z_score:.2f} (Clean Exit)"
                        ))
                    
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
                    'regime': 'TREND' if is_trending else ('REVERT' if is_reverting else 'NEUTRAL')
                })
                    
        return signals

    def _prepare_basket_data(self, data: Dict[str, pd.DataFrame], symbols: List[str]) -> pd.DataFrame:
        """Combine close prices into a single DataFrame and handle duplicate timestamps."""
        basket_data = {}
        for sym in symbols:
            if sym in data:
                # Deduplicate individual series first
                series = data[sym]['close']
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
        # Increased to 10% of capital to handle high-priced stocks like DIVISLAB (6k+)
        risk_per_trade = capital * 0.10 
        if price <= 0: return 0
        return int(risk_per_trade / price)
