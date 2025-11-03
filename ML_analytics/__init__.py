"""
ML Analytics Package for Trading Strategy Optimization

This package provides machine learning-based hyperparameter optimization
for trading strategies using historical data analysis.

Features:
- Bayesian Optimization for efficient parameter search
- Genetic Algorithms for multi-objective optimization  
- Grid Search for exhaustive parameter exploration
- Walk-forward analysis for robust validation
- Strategy parameter space definitions
- Performance metric optimization (Sharpe ratio, Calmar ratio, etc.)
"""

from .optimizer import *
from .parameter_spaces import *
from .objective_functions import *
from .validators import *
from .utils import *

__version__ = "1.0.0"
__all__ = [
    "BayesianOptimizer",
    "GeneticOptimizer", 
    "GridSearchOptimizer",
    "ParameterSpace",
    "ObjectiveFunction",
    "WalkForwardValidator",
    "OptimizationResults"
]