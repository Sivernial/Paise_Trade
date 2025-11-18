"""
Objective Functions for Strategy Optimization

Defines various objective functions to optimize strategy performance,
including risk-adjusted returns, drawdown metrics, and custom objectives.
"""

from typing import Dict, Any, Callable, List, Optional
from .constants import OptimizationResult

# Numerical computation (optional import)
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    # Fallback for isnan check
    def isnan(x):
        return x != x
    
class ObjectiveFunction:
    """Base class for optimization objective functions"""
    
    @staticmethod
    def sharpe_ratio(backtest_results: Dict[str, Any]) -> float:
        """Maximize Sharpe ratio"""
        performance = backtest_results.get('performance_metrics')
        if performance and hasattr(performance, 'sharpe_ratio'):
            return performance.sharpe_ratio if not np.isnan(performance.sharpe_ratio) else -999
        return -999
    
    @staticmethod
    def calmar_ratio(backtest_results: Dict[str, Any]) -> float:
        """Maximize Calmar ratio (annualized return / max drawdown)"""
        performance = backtest_results.get('performance_metrics')
        if performance and hasattr(performance, 'calmar_ratio'):
            return performance.calmar_ratio if not np.isnan(performance.calmar_ratio) else -999
        return -999
    
    @staticmethod
    def sortino_ratio(backtest_results: Dict[str, Any]) -> float:
        """Maximize Sortino ratio"""
        performance = backtest_results.get('performance_metrics')
        if performance and hasattr(performance, 'sortino_ratio'):
            return performance.sortino_ratio if not np.isnan(performance.sortino_ratio) else -999
        return -999
    
    @staticmethod
    def total_return(backtest_results: Dict[str, Any]) -> float:
        """Maximize total return"""
        return backtest_results.get('total_return', -999)
    
    @staticmethod
    def profit_factor(backtest_results: Dict[str, Any]) -> float:
        """Maximize profit factor"""
        performance = backtest_results.get('performance_metrics')
        if performance and hasattr(performance, 'profit_factor'):
            return performance.profit_factor if not np.isnan(performance.profit_factor) else -999
        return -999
    
    @staticmethod
    def win_rate(backtest_results: Dict[str, Any]) -> float:
        """Maximize win rate"""
        performance = backtest_results.get('performance_metrics')
        if performance and hasattr(performance, 'win_rate'):
            return performance.win_rate if not np.isnan(performance.win_rate) else -999
        return -999
    
    @staticmethod
    def risk_adjusted_return(backtest_results: Dict[str, Any], risk_weight: float = 0.5) -> float:
        """
        Custom objective: Balance return and risk
        Higher return, lower drawdown = better score
        """
        performance = backtest_results.get('performance_metrics')
        if not performance:
            return -999
            
        total_ret = getattr(performance, 'total_return', 0)
        max_dd = abs(getattr(performance, 'max_drawdown', 1))  # Convert to positive
        
        if max_dd == 0:
            max_dd = 0.001  # Avoid division by zero
            
        # Score = return - risk_penalty
        risk_penalty = risk_weight * max_dd
        score = total_ret - risk_penalty
        
        return score if not np.isnan(score) else -999
    
    @staticmethod
    def multi_objective_score(backtest_results: Dict[str, Any], 
                            weights: Dict[str, float] = None) -> float:
        """
        Multi-objective function combining multiple metrics
        Default weights favor risk-adjusted performance
        """
        if weights is None:
            weights = {
                'sharpe_ratio': 0.3,
                'total_return': 0.25,
                'win_rate': 0.2,
                'profit_factor': 0.15,
                'max_drawdown': -0.1  # Negative weight (penalty)
            }
        
        performance = backtest_results.get('performance_metrics')
        if not performance:
            return -999
            
        score = 0
        
        # Sharpe ratio component
        sharpe = getattr(performance, 'sharpe_ratio', 0)
        if not np.isnan(sharpe):
            score += weights.get('sharpe_ratio', 0) * sharpe
            
        # Total return component
        total_ret = getattr(performance, 'total_return', 0)
        if not np.isnan(total_ret):
            score += weights.get('total_return', 0) * total_ret
            
        # Win rate component
        win_rt = getattr(performance, 'win_rate', 0)
        if not np.isnan(win_rt):
            score += weights.get('win_rate', 0) * win_rt
            
        # Profit factor component
        pf = getattr(performance, 'profit_factor', 0)
        if not np.isnan(pf):
            score += weights.get('profit_factor', 0) * min(pf, 10)  # Cap at 10 to avoid outliers
            
        # Max drawdown penalty
        max_dd = abs(getattr(performance, 'max_drawdown', 0))
        if not np.isnan(max_dd):
            score += weights.get('max_drawdown', 0) * max_dd
        
        return score if not np.isnan(score) else -999
    
    @staticmethod
    def minimum_trades_filter(backtest_results: Dict[str, Any], min_trades: int = 10) -> bool:
        """Filter function to ensure minimum number of trades"""
        performance = backtest_results.get('performance_metrics')
        if performance and hasattr(performance, 'total_trades'):
            return performance.total_trades >= min_trades
        return False
    
    @staticmethod
    def drawdown_filter(backtest_results: Dict[str, Any], max_drawdown: float = 0.3) -> bool:
        """Filter function to limit maximum drawdown"""
        performance = backtest_results.get('performance_metrics')
        if performance and hasattr(performance, 'max_drawdown'):
            return abs(performance.max_drawdown) <= max_drawdown
        return False
    
    @classmethod
    def get_objective_function(cls, objective_name: str) -> Callable:
        """Get objective function by name"""
        objectives = {
            'sharpe_ratio': cls.sharpe_ratio,
            'calmar_ratio': cls.calmar_ratio,
            'sortino_ratio': cls.sortino_ratio,
            'total_return': cls.total_return,
            'profit_factor': cls.profit_factor,
            'win_rate': cls.win_rate,
            'risk_adjusted_return': cls.risk_adjusted_return,
            'multi_objective_score': cls.multi_objective_score
        }
        
        return objectives.get(objective_name, cls.sharpe_ratio)
    
    @classmethod
    def get_available_objectives(cls) -> List[str]:
        """Get list of available objective functions"""
        return [
            'sharpe_ratio',
            'calmar_ratio', 
            'sortino_ratio',
            'total_return',
            'profit_factor',
            'win_rate',
            'risk_adjusted_return',
            'multi_objective_score'
        ]
    
    @classmethod
    def create_custom_objective(cls, 
                              metrics_weights: Dict[str, float],
                              penalty_weights: Dict[str, float] = None) -> Callable:
        """
        Create a custom objective function with specified weights
        
        Args:
            metrics_weights: Dict of metric_name -> weight (positive for maximizing)
            penalty_weights: Dict of metric_name -> penalty_weight (for constraints)
        """
        if penalty_weights is None:
            penalty_weights = {}
            
        def custom_objective(backtest_results: Dict[str, Any]) -> float:
            performance = backtest_results.get('performance_metrics')
            if not performance:
                return -999
                
            score = 0
            
            # Add weighted metrics
            for metric_name, weight in metrics_weights.items():
                value = getattr(performance, metric_name, 0)
                if not np.isnan(value):
                    score += weight * value
                    
            # Add penalties
            for metric_name, penalty_weight in penalty_weights.items():
                value = getattr(performance, metric_name, 0)
                if not np.isnan(value):
                    score -= penalty_weight * abs(value)
                    
            return score if not np.isnan(score) else -999
            
        return custom_objective