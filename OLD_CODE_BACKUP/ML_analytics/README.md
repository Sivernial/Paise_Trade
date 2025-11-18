# ML Analytics Module

## Overview

The ML Analytics module provides comprehensive machine learning-based hyperparameter optimization for trading strategies. This module allows you to automatically find optimal strategy parameters using various optimization algorithms including Bayesian Optimization, Genetic Algorithms, and Grid Search.

## Folder Structure

```
ML_analytics/
├── __init__.py                 # Main module initialization
├── constants/                  # Data classes and constants
│   └── __init__.py            # OptimizationConfig, ParameterSpec, OptimizationResult
├── utils/                     # Utility functions
│   └── __init__.py            # Helper functions for data loading, backtesting integration
├── parameter_spaces.py        # Parameter search space definitions for each strategy
├── objective_functions.py     # Optimization objective functions (Sharpe, Calmar, etc.)
├── optimizer.py              # Core optimization algorithms (Bayesian, Genetic, Grid Search)
├── optimization_runner.py    # Main interface for running optimization experiments
└── requirements.txt          # Optional ML dependencies
```

## Key Components

### 1. Constants (`constants/`)

- **OptimizationConfig**: Configuration for optimization runs (evaluations, jobs, random state)
- **ParameterSpec**: Specification for individual strategy parameters (type, bounds, defaults)
- **OptimizationResult**: Results structure containing parameters, objective value, and metrics
- **Default values**: Common bounds and settings for optimization algorithms

### 2. Utils (`utils/`)

- **create_backtest_wrapper()**: Integrates backtest engine with optimization algorithms
- **load_historical_data_for_optimization()**: Loads historical data for multiple symbols
- **validate_optimization_inputs()**: Input validation for optimization parameters
- **extract_metrics_from_backtest()**: Extracts performance metrics from backtest results
- **print_optimization_summary()**: Formatted output for optimization results

### 3. Parameter Spaces (`parameter_spaces.py`)

Defines search spaces for each strategy:

- **Moving Average Crossover**: fast_period (5-50), slow_period (10-200)
- **RSI Mean Reversion**: rsi_period (5-50), oversold (10-40), overbought (60-90)
- **Bollinger Bands**: bb_period (10-50), bb_std (1.0-3.0), strategy_type (breakout/mean_reversion)
- **Multi-Indicator**: Combinations of MA, RSI, BB parameters
- **Adaptive Momentum Breakout**: lookback_period (10-100), momentum_threshold (0.01-0.10)

### 4. Objective Functions (`objective_functions.py`)

Available optimization targets:

- **sharpe_ratio**: Risk-adjusted returns (return/volatility)
- **calmar_ratio**: Return/max drawdown ratio
- **multi_objective**: Weighted combination of multiple metrics
- **sortino_ratio**: Downside risk-adjusted returns
- **profit_factor**: Gross profit/gross loss ratio

### 5. Optimizers (`optimizer.py`)

Three optimization algorithms:

- **GridSearchOptimizer**: Exhaustive search over parameter grid
- **BayesianOptimizer**: Gaussian Process-based optimization (requires scikit-optimize)
- **GeneticOptimizer**: Evolutionary algorithm optimization (requires DEAP)

### 6. Main Interface (`optimization_runner.py`)

The `MLOptimizationInterface` class provides:

- **optimize_strategy()**: Single strategy optimization
- **compare_strategies()**: Multi-strategy comparison
- **run_walk_forward_optimization()**: Time-series validation

## Usage Examples

### Basic Strategy Optimization

```python
from ML_analytics.optimization_runner import MLOptimizationInterface

# Initialize the interface
ml_optimizer = MLOptimizationInterface()

# Optimize a single strategy
result = ml_optimizer.optimize_strategy(
    strategy_name='moving_average_crossover',
    symbols=['NIFTY'],
    optimizer_type='bayesian',
    objective_function='sharpe_ratio',
    max_evaluations=100
)

print(f"Best Parameters: {result['best_parameters']}")
print(f"Best Sharpe Ratio: {result['best_objective_value']:.4f}")
```

### Strategy Comparison

```python
# Compare multiple strategies
comparison = ml_optimizer.compare_strategies(
    strategies=['moving_average_crossover', 'rsi_mean_reversion', 'bollinger_band'],
    symbols=['NIFTY'],
    optimizer_type='bayesian',
    max_evaluations_per_strategy=50
)

# Results ranked by objective function
for strategy, result in comparison.items():
    print(f"{strategy}: {result['best_objective_value']:.4f}")
```

### Walk-Forward Optimization

```python
# Test parameter stability over time
walk_forward = ml_optimizer.run_walk_forward_optimization(
    strategy_name='moving_average_crossover',
    symbols=['NIFTY'],
    training_window_months=12,
    reoptimization_frequency_months=3
)

print(f"Average Parameter Stability: {walk_forward['summary_statistics']['avg_parameter_stability']:.4f}")
```

## Dependencies

### Required (Core functionality)

- Python standard library modules (typing, datetime, json, etc.)

### Optional (Advanced optimization)

- **scikit-optimize** (for Bayesian optimization): `pip install scikit-optimize`
- **DEAP** (for genetic algorithms): `pip install deap`
- **numpy** (for numerical computations): `pip install numpy`
- **pandas** (for data handling): `pip install pandas`

The module gracefully handles missing optional dependencies and provides fallback implementations.

## Integration with Backtesting System

The ML Analytics module integrates seamlessly with the existing backtesting infrastructure:

1. **Backtest Engine**: Uses the core `BacktestEngine` class for strategy evaluation
2. **Data Manager**: Leverages `DataManager` for historical data loading
3. **Strategy Classes**: Works with all strategy implementations in the `strategies/` folder
4. **Performance Metrics**: Uses the same performance calculation system as manual backtesting

## Performance Considerations

- **Parallel Processing**: Grid search supports parallel evaluation (`n_jobs` parameter)
- **Result Caching**: Optimization results are saved to JSON files for later analysis
- **Progress Tracking**: Real-time progress updates during optimization
- **Memory Management**: Efficient handling of large parameter spaces and historical data

## Configuration

Optimization behavior can be customized through `OptimizationConfig`:

```python
from ML_analytics.constants import OptimizationConfig

config = OptimizationConfig(
    strategy_name='moving_average_crossover',
    objective_function='sharpe_ratio',
    max_evaluations=200,        # More evaluations for better results
    n_jobs=4,                   # Parallel processing
    random_state=42,            # Reproducible results
    save_results=True,          # Save to JSON files
    results_dir='my_results'    # Custom output directory
)
```

## Error Handling

The module includes robust error handling:

- **Missing Dependencies**: Graceful degradation when optional packages unavailable
- **Data Issues**: Handles missing or invalid historical data
- **Parameter Validation**: Checks parameter bounds and types before optimization
- **Backtest Failures**: Continues optimization even if individual evaluations fail

## Best Practices

1. **Start Small**: Begin with grid search and small evaluation budgets for testing
2. **Use Bayesian Optimization**: Most efficient for continuous parameters
3. **Validate Results**: Use walk-forward optimization to test parameter stability
4. **Monitor Progress**: Watch for convergence in optimization algorithms
5. **Save Results**: Enable result saving for later analysis and comparison

---

This module transforms manual parameter tuning into an automated, data-driven optimization process, enabling systematic discovery of high-performing strategy configurations.
