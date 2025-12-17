
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

    def check_correlation(self, current_positions: list, new_pair: tuple) -> bool:
        """
        Future implementation: Check if new_pair is highly correlated with existing positions.
        """
        return True
