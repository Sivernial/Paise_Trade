"""
Results Processing Utilities

Contains functions for extracting, processing, and displaying
optimization and backtest results.
"""

from typing import Dict, Any


def extract_metrics_from_backtest(backtest_result: Dict[str, Any]) -> Dict[str, float]:
    """
    Extract key metrics from backtest results
    
    Args:
        backtest_result: Results from BacktestEngine
        
    Returns:
        Dictionary of extracted metrics
    """
    metrics = {}
    
    if not backtest_result or 'performance_metrics' not in backtest_result:
        return metrics
    
    performance = backtest_result['performance_metrics']
    
    # Extract common metrics
    metric_names = [
        'total_return', 'annualized_return', 'volatility', 'sharpe_ratio',
        'max_drawdown', 'win_rate', 'calmar_ratio'
    ]
    
    for metric in metric_names:
        value = getattr(performance, metric, None)
        if value is not None:
            try:
                metrics[metric] = float(value)
            except (ValueError, TypeError):
                metrics[metric] = 0.0
    
    return metrics


def print_optimization_summary(strategy_name: str,
                             optimizer_type: str,
                             objective_function: str,
                             best_parameters: Dict[str, Any],
                             best_objective_value: float,
                             best_metrics: Dict[str, Any]):
    """
    Print a formatted optimization summary
    
    Args:
        strategy_name: Name of the optimized strategy
        optimizer_type: Type of optimizer used
        objective_function: Objective function optimized
        best_parameters: Best parameter set found
        best_objective_value: Best objective value achieved
        best_metrics: Best metrics achieved
    """
    print(f"\n{'='*80}")
    print(f"OPTIMIZATION SUMMARY")
    print(f"{'='*80}")
    print(f"Strategy: {strategy_name}")
    print(f"Optimizer: {optimizer_type}")
    print(f"Objective Function: {objective_function}")
    print(f"\nBest Parameters:")
    for param, value in best_parameters.items():
        if isinstance(value, float):
            print(f"  {param}: {value:.4f}")
        else:
            print(f"  {param}: {value}")
    print(f"\nBest Objective Value: {best_objective_value:.4f}")
    print(f"\nKey Metrics:")
    for metric, value in best_metrics.items():
        if isinstance(value, (int, float)):
            print(f"  {metric}: {value:.4f}")
        else:
            print(f"  {metric}: {value}")
    print(f"{'='*80}")


def print_strategy_comparison(results: Dict[str, Any], objective: str):
    """
    Print strategy comparison results
    
    Args:
        results: Dictionary of strategy results
        objective: Objective function used for ranking
    """
    print(f"\n{'='*80}")
    print(f"STRATEGY COMPARISON RESULTS")
    print(f"{'='*80}")
    print(f"Objective Function: {objective}")
    print(f"\nRanking (by {objective}):")
    
    # Sort strategies by objective value
    sorted_strategies = sorted(
        results.items(),
        key=lambda x: x[1]['best_objective_value'],
        reverse=True
    )
    
    for i, (strategy, result) in enumerate(sorted_strategies, 1):
        obj_value = result['best_objective_value']
        sharpe = result['best_metrics'].get('sharpe_ratio', 'N/A')
        max_dd = result['best_metrics'].get('max_drawdown', 'N/A')
        
        print(f"{i:2d}. {strategy:25} | "
              f"Objective: {obj_value:7.4f} | "
              f"Sharpe: {sharpe:7.4f} | "
              f"Max DD: {max_dd:7.4f}")
    
    print(f"{'='*80}")