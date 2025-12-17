
import numpy as np
import pandas as pd
from scipy.optimize import minimize
import logging

logger = logging.getLogger(__name__)

class PortfolioOptimizer:
    """
    Implements Modern Portfolio Theory (Markowitz Mean-Variance Optimization).
    Allocates capital optimally across different assets/pairs to maximize Sharpe Ratio.
    """
    
    def __init__(self, risk_free_rate: float = 0.05):
        self.risk_free_rate = risk_free_rate
        
    def optimize(self, price_data: pd.DataFrame, min_weight: float = 0.0, max_weight: float = 0.5) -> dict:
        """
        Optimize weights for Maximum Sharpe Ratio.
        :param price_data: DataFrame where columns are Asset/Pair names and rows are daily closing prices (or equity curves).
        :return: Dictionary of optimal weights {asset: weight}
        """
        if price_data.empty:
            return {}
            
        # Calculate Daily Returns
        returns_df = price_data.pct_change().dropna()
        
        if returns_df.empty:
            logger.warning("Not enough data for optimization")
            return {col: 1.0/len(price_data.columns) for col in price_data.columns}
            
        mean_returns = returns_df.mean()
        cov_matrix = returns_df.cov()
        num_assets = len(mean_returns)
        
        # Objective Function (Negative Sharpe Ratio)
        def negative_sharpe(weights):
            portfolio_return = np.sum(mean_returns * weights) * 252
            portfolio_std = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights))) * np.sqrt(252)
            if portfolio_std == 0: return 0
            sharpe = (portfolio_return - self.risk_free_rate) / portfolio_std
            return -sharpe
            
        # Constraints: Sum of weights = 1
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        
        # Bounds: min_weight <= w <= max_weight
        bounds = tuple((min_weight, max_weight) for _ in range(num_assets))
        
        # Initial Guess (Equal weights)
        init_guess = num_assets * [1. / num_assets]
        
        try:
            result = minimize(
                negative_sharpe, 
                init_guess, 
                method='SLSQP', 
                bounds=bounds, 
                constraints=constraints
            )
            
            optimal_weights = result.x
            
            # Create Result Dictionary
            weight_dict = {
                asset: round(weight, 4) 
                for asset, weight in zip(price_data.columns, optimal_weights)
            }
            
            # Calculate Portfolio Metrics
            port_ret = np.sum(mean_returns * optimal_weights) * 252
            port_vol = np.sqrt(np.dot(optimal_weights.T, np.dot(cov_matrix, optimal_weights))) * np.sqrt(252)
            sharpe = (port_ret - self.risk_free_rate) / port_vol if port_vol > 0 else 0
            
            logger.info(f"Optimization Success. Sharpe: {sharpe:.2f}")
            
            return {
                'weights': weight_dict,
                'metrics': {
                    'expected_return': port_ret,
                    'volatility': port_vol,
                    'sharpe_ratio': sharpe
                }
            }
            
        except Exception as e:
            logger.error(f"Optimization Failed: {e}")
            return {}
