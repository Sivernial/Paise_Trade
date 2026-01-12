import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging
from .base_strategy import BaseStrategy
from Common import Signal, SignalType
from Common.quant_utils import calculate_pca_residuals, MarketRegimeDetector

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
        self.z_threshold = self.params.get('z_threshold', 2.5)
        self.n_components = self.params.get('n_components', 1)
        self.lookback = self.params.get('lookback', 300)
        
        self.regime_detector = MarketRegimeDetector(n_regimes=2)
        
    def generate_signals(self, data: Dict[str, pd.DataFrame], 
                        current_date: datetime, capital: float = 100000) -> List[Signal]:
        signals = []
        
        for basket_name, symbols in self.baskets.items():
            basket_df = self._prepare_basket_data(data, symbols)
            if basket_df.empty or len(basket_df) < self.lookback:
                continue
                
            log_returns = np.log(basket_df / basket_df.shift(1)).dropna()
            
            # 2. PCA Residual Extraction
            residuals = calculate_pca_residuals(log_returns.tail(self.lookback), n_components=self.n_components)
            cum_residuals = residuals.cumsum()
            
            # 3. Analyze each asset
            for symbol in symbols:
                if symbol not in cum_residuals.columns: continue
                res_series = cum_residuals[symbol]
                
                # Z-Score
                mean_res = res_series.mean()
                std_res = res_series.std()
                current_res = res_series.iloc[-1]
                z_score = (current_res - mean_res) / std_res if std_res > 0 else 0
                
                # V3 BASELINE REVERSION LOGIC
                price = basket_df[symbol].iloc[-1]
                if z_score > self.z_threshold:
                    signals.append(Signal(
                        symbol=symbol,
                        signal_type=SignalType.SELL,
                        price=price,
                        timestamp=current_date,
                        quantity=self._calculate_quantity(capital, price),
                        reason=f"PCA Z={z_score:.2f}"
                    ))
                elif z_score < -self.z_threshold:
                    signals.append(Signal(
                        symbol=symbol,
                        signal_type=SignalType.BUY,
                        price=price,
                        timestamp=current_date,
                        quantity=self._calculate_quantity(capital, price),
                        reason=f"PCA Z={z_score:.2f}"
                    ))
                    
        return signals

    def _prepare_basket_data(self, data: Dict[str, pd.DataFrame], symbols: List[str]) -> pd.DataFrame:
        """Combine close prices into a single DataFrame."""
        basket_data = {}
        for sym in symbols:
            if sym in data:
                basket_data[sym] = data[sym]['close']
        
        df = pd.DataFrame(basket_data).dropna()
        if len(df.columns) < 2:
             return pd.DataFrame() 
        return df

    def _calculate_quantity(self, capital: float, price: float) -> int:
        """Original Fixed-Dollar position sizing."""
        risk_per_trade = capital * 0.01 
        if price <= 0: return 0
        return int(risk_per_trade / price)
