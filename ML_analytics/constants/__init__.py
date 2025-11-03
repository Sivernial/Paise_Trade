"""
Constants and Data Classes for ML Analytics

Contains all dataclass definitions and constants used across the ML optimization system.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Tuple, Union, Optional

@dataclass
class ParameterSpec:
    """Specification for a strategy parameter"""
    param_type: str  # 'int', 'float', 'categorical', 'bool'
    bounds: Union[Tuple[float, float], List[Any]]  # (min, max) for numeric, list for categorical
    default: Any
    description: str = ""

@dataclass
class OptimizationConfig:
    """Configuration for optimization runs"""
    strategy_name: str
    objective_function: str
    max_evaluations: int = 100
    n_jobs: int = 1  # Parallel processes
    random_state: int = 42
    validation_split: float = 0.3  # For walk-forward validation
    save_results: bool = True
    results_dir: str = "optimization_results"

@dataclass
class OptimizationResult:
    """Results from an optimization run"""
    parameters: Dict[str, Any]
    objective_value: float
    metrics: Dict[str, float]
    backtest_results: Optional[Dict[str, Any]] = None
    evaluation_time: Optional[float] = None
    optimization_metadata: Optional[Dict[str, Any]] = None

# Constants for optimization algorithms
OPTIMIZER_TYPES = {
    'grid_search': 'Grid Search',
    'bayesian': 'Bayesian Optimization',
    'genetic': 'Genetic Algorithm'
}

OBJECTIVE_FUNCTIONS = {
    'sharpe_ratio': 'Sharpe Ratio',
    'calmar_ratio': 'Calmar Ratio', 
    'multi_objective': 'Multi-Objective Score'
}

# Default optimization settings
DEFAULT_OPTIMIZATION_CONFIG = {
    'max_evaluations': 100,
    'n_jobs': 1,
    'random_state': 42,
    'validation_split': 0.3,
    'save_results': True
}

# Parameter bounds for common strategy types
DEFAULT_PARAMETER_BOUNDS = {
    'moving_average': {
        'fast_period': (5, 50),
        'slow_period': (10, 200)
    },
    'rsi': {
        'rsi_period': (5, 50),
        'oversold_threshold': (10, 40),
        'overbought_threshold': (60, 90)
    },
    'bollinger_bands': {
        'bb_period': (10, 50),
        'bb_std': (1.0, 3.0)
    }
}

# Optimization algorithm specific constants
BAYESIAN_OPTIMIZATION_DEFAULTS = {
    'n_initial_points': 10,
    'acq_func': 'EI',  # Expected Improvement
    'acq_optimizer': 'auto'
}

GENETIC_ALGORITHM_DEFAULTS = {
    'population_size': 50,
    'generations': 20,
    'crossover_prob': 0.7,
    'mutation_prob': 0.2,
    'tournament_size': 3
}

GRID_SEARCH_DEFAULTS = {
    'grid_resolution': 5
}