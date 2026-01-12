
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class RiskManager:
    """
    Manages position sizing and risk based on Volatility (ATR).
    Formula: Position Size = (Account Value * Risk Per Trade %) / (ATR * Multiplier)
    """
    
    def __init__(self, risk_per_trade_pct: float = 0.02, atr_multiplier: float = 2.0, max_position_pct: float = 0.2):
        self.risk_per_trade_pct = risk_per_trade_pct
        self.atr_multiplier = atr_multiplier
        self.max_position_pct = max_position_pct
        
    def calculate_size(self, capital: float, price: float, atr: float) -> int:
        """
        Calculate quantity based on ATR risk.
        Risk Amount = Capital * Risk%
        Stop Distance = ATR * Multiplier
        Quantity = Risk Amount / Stop Distance
        """
        if price <= 0 or atr <= 0:
            return 0
            
        risk_amount = capital * self.risk_per_trade_pct
        stop_distance = atr * self.atr_multiplier
        
        # Avoid division by zero or tiny stops
        if stop_distance < (price * 0.001): # Min stop 0.1%
             stop_distance = price * 0.001
             
        quantity = int(risk_amount / stop_distance)
        
        # Max Position Value Cap (e.g., Don't put 50% capital in one trade)
        max_cost = capital * self.max_position_pct
        if (quantity * price) > max_cost:
            quantity = int(max_cost / price)
            
        return quantity

    def check_correlation(self, current_positions: list, new_pair: tuple, market_data: dict, lookback: int = 40) -> bool:
        """
        Check if the new_pair components are highly correlated with any existing position.
        Returns False if correlation > 0.7 (Too much exposure to same moves).
        """
        if not current_positions:
            return True
            
        new_assets = [new_pair[0], new_pair[1]]
        
        for new_asset in new_assets:
            if new_asset not in market_data: continue
            
            new_series = market_data[new_asset]['close'].pct_change().tail(lookback).fillna(0)
            
            for existing_pos in current_positions:
                if existing_pos not in market_data: continue
                
                # Don't compare with itself (though strictly shouldn't happen if checking new entries)
                if existing_pos == new_asset: 
                    # Actually if we already hold it, we might be adding size, which is fine for the strategy logic
                    continue
                    
                pos_series = market_data[existing_pos]['close'].pct_change().tail(lookback).fillna(0)
                
                # Check Length match
                min_len = min(len(new_series), len(pos_series))
                if min_len < 10: continue
                
                corr = new_series.iloc[-min_len:].corr(pos_series.iloc[-min_len:])
                
                if abs(corr) > 0.75:
                    logger.info(f"🚫 High Correlation detected: {new_asset} vs {existing_pos} (Corr: {corr:.2f})")
                    return False
                    
        return True
