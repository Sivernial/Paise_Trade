"""
Utility Functions for ML Analytics

Contains helper functions for data loading, backtest integration, 
and other common operations used across the optimization system.
"""

from typing import Dict, Any, List, Callable
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

def create_backtest_wrapper(backtest_engine):
    """
    Create a wrapper function for the backtest engine that's compatible with optimization
    
    Args:
        backtest_engine: BacktestEngine instance
        
    Returns:
        Function compatible with optimizers
    """
    def backtest_wrapper(strategy_name: str, 
                        parameters: Dict[str, Any], 
                        historical_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Wrapper function for backtesting
        
        Args:
            strategy_name: Name of strategy to test
            parameters: Strategy parameters
            historical_data: Historical price data
            
        Returns:
            Backtest results dictionary
        """
        try:
            # Extract data for backtest
            symbol = list(historical_data.keys())[0]  # Use first symbol
            data = historical_data[symbol]
            
            # Run backtest
            results = backtest_engine.run_backtest(
                strategy_name=strategy_name,
                symbol=symbol,
                data=data,
                strategy_params=parameters,
                generate_plots=False  # No plots during optimization
            )
            
            return results
            
        except Exception as e:
            print(f"Error in backtest wrapper: {e}")
            return {'performance_metrics': None}
    
    return backtest_wrapper

def load_historical_data_for_optimization(symbols: List[str], 
                                        data_manager) -> Dict[str, Any]:
    """
    Load historical data for optimization
    
    Args:
        symbols: List of symbols to load
        data_manager: DataManager instance
        
    Returns:
        Dictionary of historical data
    """
    historical_data = {}
    
    for symbol in symbols:
        try:
            # Load historical data using data manager
            data = data_manager.get_historical_data(symbol)
            if data is not None and not data.empty:
                historical_data[symbol] = data
            else:
                print(f"Warning: No data available for {symbol}")
                
        except Exception as e:
            print(f"Error loading data for {symbol}: {e}")
            continue
    
    return historical_data

def validate_optimization_inputs(strategy_name: str,
                               optimizer_type: str,
                               objective_function: str,
                               available_strategies: List[str],
                               available_optimizers: List[str],
                               available_objectives: List[str]) -> bool:
    """
    Validate optimization inputs
    
    Args:
        strategy_name: Strategy to validate
        optimizer_type: Optimizer to validate
        objective_function: Objective to validate
        available_strategies: List of available strategies
        available_optimizers: List of available optimizers
        available_objectives: List of available objectives
        
    Returns:
        True if all inputs are valid
        
    Raises:
        ValueError: If any input is invalid
    """
    if strategy_name not in available_strategies:
        raise ValueError(f"Unknown strategy: {strategy_name}. Available: {available_strategies}")
    
    if optimizer_type not in available_optimizers:
        raise ValueError(f"Unknown optimizer: {optimizer_type}. Available: {available_optimizers}")
    
    if objective_function not in available_objectives:
        raise ValueError(f"Unknown objective: {objective_function}. Available: {available_objectives}")
    
    return True

def format_optimization_results(result) -> Dict[str, Any]:
    """
    Format optimization results for consistent output
    
    Args:
        result: OptimizationResult object
        
    Returns:
        Formatted results dictionary
    """
    return {
        'best_parameters': result.parameters,
        'best_objective_value': result.objective_value,
        'best_metrics': result.metrics,
        'evaluation_time': getattr(result, 'evaluation_time', None),
        'metadata': getattr(result, 'optimization_metadata', {})
    }

def calculate_parameter_stability(current_params: Dict[str, Any], 
                                previous_params: Dict[str, Any],
                                parameter_space: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate parameter stability between optimization runs
    
    Args:
        current_params: Current optimization parameters
        previous_params: Previous optimization parameters
        parameter_space: Parameter space definitions
        
    Returns:
        Dictionary with stability metrics
    """
    if not previous_params:
        return {'stability_score': 1.0, 'parameter_changes': 0}
    
    stability_scores = []
    changes = 0
    
    for param_name, current_value in current_params.items():
        if param_name in previous_params:
            prev_value = previous_params[param_name]
            
            if isinstance(current_value, (int, float)) and isinstance(prev_value, (int, float)):
                # Normalized difference for numeric parameters
                if param_name in parameter_space:
                    spec = parameter_space[param_name]
                    if spec.param_type in ['int', 'float']:
                        min_val, max_val = spec.bounds
                        param_range = max_val - min_val
                        if param_range > 0:
                            diff = abs(current_value - prev_value) / param_range
                            stability_score = 1.0 - diff
                            stability_scores.append(stability_score)
                            if stability_score < 1.0:
                                changes += 1
            else:
                # Categorical parameters
                is_same = current_value == prev_value
                stability_scores.append(1.0 if is_same else 0.0)
                if not is_same:
                    changes += 1
    
    overall_stability = sum(stability_scores) / len(stability_scores) if stability_scores else 1.0
    
    return {
        'stability_score': overall_stability,
        'parameter_changes': changes,
        'total_parameters': len(stability_scores)
    }

def extract_metrics_from_backtest(backtest_results: Dict[str, Any]) -> Dict[str, float]:
    """
    Extract key metrics from backtest results
    
    Args:
        backtest_results: Results from backtest engine
        
    Returns:
        Dictionary of extracted metrics
    """
    if not backtest_results or 'performance_metrics' not in backtest_results:
        return {}
        
    performance = backtest_results['performance_metrics']
    if not performance:
        return {}
    
    metrics = {}
    metric_names = [
        'total_return', 'annualized_return', 'volatility', 'sharpe_ratio',
        'max_drawdown', 'win_rate', 'profit_factor', 'total_trades',
        'calmar_ratio', 'sortino_ratio'
    ]
    
    for metric in metric_names:
        value = getattr(performance, metric, None)
        if value is not None:
            try:
                # Handle potential numpy types and ensure float conversion
                metrics[metric] = float(value)
            except (ValueError, TypeError):
                # Skip metrics that can't be converted to float
                continue
                
    return metrics

def create_date_ranges_for_walk_forward(total_months: int = 24,
                                      training_window_months: int = 12,
                                      reoptimization_frequency_months: int = 3) -> List[Dict[str, str]]:
    """
    Create date ranges for walk-forward optimization
    
    Args:
        total_months: Total period to test
        training_window_months: Training window size
        reoptimization_frequency_months: How often to reoptimize
        
    Returns:
        List of date range dictionaries
    """
    from datetime import datetime, timedelta
    
    periods = []
    end_date = datetime.now()
    current_end = end_date
    
    while len(periods) * reoptimization_frequency_months < total_months:
        train_start = current_end - timedelta(days=training_window_months * 30)
        train_end = current_end - timedelta(days=reoptimization_frequency_months * 30)
        test_start = train_end
        test_end = current_end
        
        # Ensure test period is valid
        if test_start >= test_end:
            break
            
        periods.append({
            'train_start': train_start.strftime('%Y-%m-%d'),
            'train_end': train_end.strftime('%Y-%m-%d'),
            'test_start': test_start.strftime('%Y-%m-%d'),
            'test_end': test_end.strftime('%Y-%m-%d')
        })
        
        current_end = test_start
    
    periods.reverse()  # Chronological order
    return periods

def print_optimization_summary(strategy_name: str,
                             optimizer_type: str,
                             objective_function: str,
                             best_parameters: Dict[str, Any],
                             best_objective_value: float,
                             best_metrics: Dict[str, float]):
    """
    Print a formatted optimization summary
    
    Args:
        strategy_name: Name of optimized strategy
        optimizer_type: Type of optimizer used
        objective_function: Objective function optimized
        best_parameters: Best parameters found
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
        objective: Objective function name
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