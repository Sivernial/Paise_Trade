"""
ML-based Hyperparameter Optimization Runner

This script provides a complete interface for running hyperparameter optimization
on trading strategies using historical data.
"""

import sys
import os
from pathlib import Path
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Core imports
from core.backtesting import BacktestEngine
from core.data_manager import DataManager
from core.config_manager import ConfigManager
from kiteconnect import KiteConnect
import pandas as pd

# ML Analytics imports
from .optimizer import OptimizationRunner
from .constants import OptimizationConfig
from .parameter_spaces import ParameterSpace
from .objective_functions import ObjectiveFunction
from .utils import create_backtest_wrapper, extract_metrics_from_backtest, print_optimization_summary, print_strategy_comparison

# Common Indian stock instrument tokens (you can add more)
STOCK_TOKENS = {
    'RELIANCE': 738561,
    'TCS': 2953217,
    'HDFCBANK': 341249,
    'INFY': 408065,
    'HINDUNILVR': 356865,
    'ICICIBANK': 1270529,
    'SBIN': 779521,
    'BHARTIARTL': 2714625,
    'ITC': 424961,
    'WIPRO': 969473,
    'LT': 2939649,
    'HCLTECH': 1850625,
    'AXISBANK': 1510401,
    'MARUTI': 2815745,
    'ASIANPAINT': 60417
}

def get_instrument_token(symbol: str) -> int:
    """Get instrument token for a symbol."""
    symbol = symbol.upper()
    if symbol in STOCK_TOKENS:
        return STOCK_TOKENS[symbol]
    else:
        raise ValueError(f"Instrument token not found for symbol: {symbol}. Available symbols: {list(STOCK_TOKENS.keys())}")

def fetch_historical_data(kite, symbol, instrument_token, days_back=60, interval="15minute"):
    """
    Fetch historical data from Zerodha in chunks to respect API interval limits.
    Intraday (minute/hour) is capped at ~60 days per call.
    """
    print(f"📊 Fetching {symbol} historical data...")
    print(f"📅 Period: Last {days_back} days")
    print(f"⏰ Timeframe: {interval}")

    # Per-interval max window (days). Adjust if your API plan differs.
    intraday_intervals = {'minute', '3minute', '5minute', '10minute', '15minute', '30minute', 'hour'}
    max_window_days = 60 if interval in intraday_intervals else 3650  # ~10 years for 'day'

    to_date = datetime.now()
    from_date = to_date - timedelta(days=days_back)

    all_frames = []
    cur_to = to_date

    while cur_to > from_date:
        window_from = max(from_date, cur_to - timedelta(days=max_window_days - 1))

        try:
            historical_data = kite.historical_data(
                instrument_token=instrument_token,
                from_date=window_from,
                to_date=cur_to,
                interval=interval
            )
        except Exception as e:
            print(f"❌ Error fetching chunk {window_from.date()} -> {cur_to.date()}: {e}")
            break

        df_chunk = pd.DataFrame(historical_data)
        if df_chunk.empty:
            # No more data returned—stop
            break

        # Normalize
        df_chunk['date'] = pd.to_datetime(df_chunk['date'])
        all_frames.append(df_chunk)

        # Move to previous window (leave a 1-day gap to avoid overlap)
        cur_to = window_from - timedelta(days=1)

    if not all_frames:
        print(f"❌ No data received for {symbol}")
        return None

    # Concatenate and clean
    df = pd.concat(all_frames, ignore_index=True)
    df.drop_duplicates(subset=['date'], inplace=True)
    df.sort_values('date', inplace=True)
    df.set_index('date', inplace=True)

    # Standardize column names to match the rest of the code
    df.columns = ['open', 'high', 'low', 'close', 'volume']

    print(f"✅ Data fetched successfully!")
    return df

class MLOptimizationInterface:
    """
    Main interface for ML-based hyperparameter optimization
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize the optimization interface
        
        Args:
            config_path: Path to configuration file (optional)
        """
        # Initialize core components
        if config_path:
            self.config_manager = ConfigManager(config_dir=config_path)
        else:
            self.config_manager = ConfigManager()  # Use default config directory
        
        # Initialize Kite connection
        self.kite = self._initialize_kite_connection()
        
        # Initialize data manager with Kite connection
        self.data_manager = DataManager(self.kite)
        self.backtest_engine = BacktestEngine()
        
        # Create backtest wrapper for optimization
        self.backtest_wrapper = create_backtest_wrapper(self.backtest_engine)
        
        # Initialize optimization runner
        self.optimization_runner = OptimizationRunner(self.backtest_wrapper)
        
        # Available strategies and optimizers
        self.available_strategies = [
            'moving_average_crossover',
            'rsi_mean_reversion', 
            'bollinger_band',
            'multi_indicator',
            'adaptive_momentum_breakout'
        ]
        
        self.available_optimizers = ['grid_search', 'bayesian', 'genetic']
        self.available_objectives = ['sharpe_ratio', 'calmar_ratio', 'multi_objective']
        
        print("ML Optimization Interface initialized successfully!")
        print(f"Available strategies: {self.available_strategies}")
        print(f"Available optimizers: {self.available_optimizers}")
        print(f"Available objectives: {self.available_objectives}")
    
    def _initialize_kite_connection(self):
        """Initialize Kite connection using environment variables."""
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            api_key = os.getenv('API_KEY')
            access_token = os.getenv('ACCESS_TOKEN')
            
            if not api_key or not access_token:
                raise ValueError("API_KEY and ACCESS_TOKEN must be set in .env file")
            
            kite = KiteConnect(api_key=api_key)
            kite.set_access_token(access_token)
            
            print("✅ Kite connection initialized successfully!")
            return kite
            
        except Exception as e:
            print(f"❌ Failed to initialize Kite connection: {e}")
            raise
    
    def optimize_strategy(self,
                         strategy_name: str,
                         symbols: List[str],
                         start_date: str = None,
                         end_date: str = None,
                         optimizer_type: str = 'bayesian',
                         objective_function: str = 'sharpe_ratio',
                         max_evaluations: int = 100,
                         n_jobs: int = 1,
                         save_results: bool = True) -> Dict[str, Any]:
        """
        Optimize parameters for a trading strategy
        
        Args:
            strategy_name: Name of the strategy to optimize
            symbols: List of symbols to test on
            start_date: Start date for historical data (YYYY-MM-DD)
            end_date: End date for historical data (YYYY-MM-DD)
            optimizer_type: Type of optimizer to use
            objective_function: Objective function to optimize
            max_evaluations: Maximum number of parameter evaluations
            n_jobs: Number of parallel jobs (for applicable optimizers)
            save_results: Whether to save optimization results
            
        Returns:
            Dictionary containing optimization results
        """
        # Validate inputs
        if strategy_name not in self.available_strategies:
            raise ValueError(f"Unknown strategy: {strategy_name}. Available: {self.available_strategies}")
        
        if optimizer_type not in self.available_optimizers:
            raise ValueError(f"Unknown optimizer: {optimizer_type}. Available: {self.available_optimizers}")
        
        if objective_function not in self.available_objectives:
            raise ValueError(f"Unknown objective: {objective_function}. Available: {self.available_objectives}")
        
        # Set default date range if not provided
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365*2)).strftime('%Y-%m-%d')  # 2 years
        
        print(f"\n{'='*80}")
        print(f"STARTING ML HYPERPARAMETER OPTIMIZATION")
        print(f"{'='*80}")
        print(f"Strategy: {strategy_name}")
        print(f"Symbols: {symbols}")
        print(f"Date Range: {start_date} to {end_date}")
        print(f"Optimizer: {optimizer_type}")
        print(f"Objective: {objective_function}")
        print(f"Max Evaluations: {max_evaluations}")
        print(f"{'='*80}")
        
        # Load historical data
        print("Loading historical data...")
        historical_data = self._load_historical_data(symbols, start_date, end_date)
        
        if not historical_data:
            raise ValueError("No historical data available for the specified symbols and date range")
        
        print(f"Loaded data for {len(historical_data)} symbols")
        
        # Create optimization configuration
        config = OptimizationConfig(
            strategy_name=strategy_name,
            objective_function=objective_function,
            max_evaluations=max_evaluations,
            n_jobs=n_jobs,
            save_results=save_results,
            results_dir=f"ML_analytics/results/{strategy_name}"
        )
        
        # Run optimization
        try:
            result = self.optimization_runner.run_optimization(
                strategy_name=strategy_name,
                historical_data=historical_data,
                config=config,
                optimizer_type=optimizer_type
            )
            
            # Format results for return
            optimization_results = {
                'strategy_name': strategy_name,
                'optimizer_type': optimizer_type,
                'objective_function': objective_function,
                'optimization_config': {
                    'symbols': symbols,
                    'start_date': start_date,
                    'end_date': end_date,
                    'max_evaluations': max_evaluations,
                    'n_jobs': n_jobs
                },
                'best_parameters': result.parameters,
                'best_objective_value': result.objective_value,
                'best_metrics': result.metrics,
                'total_evaluations': len(self.optimization_runner.optimizers)
            }
            
            # Print summary
            print_optimization_summary(
                strategy_name=strategy_name,
                optimizer_type=optimizer_type,
                objective_function=objective_function,
                best_parameters=result.parameters,
                best_objective_value=result.objective_value,
                best_metrics=result.metrics
            )
            
            return optimization_results
            
        except Exception as e:
            print(f"Error during optimization: {e}")
            raise
    
    def compare_strategies(self,
                          strategies: List[str],
                          symbols: List[str],
                          optimizer_type: str = 'bayesian',
                          objective_function: str = 'sharpe_ratio',
                          max_evaluations_per_strategy: int = 50) -> Dict[str, Any]:
        """
        Compare multiple strategies using optimization
        
        Args:
            strategies: List of strategies to compare
            symbols: List of symbols to test on
            optimizer_type: Type of optimizer to use
            objective_function: Objective function to optimize
            max_evaluations_per_strategy: Max evaluations per strategy
            
        Returns:
            Dictionary containing comparison results
        """
        print(f"\n{'='*80}")
        print(f"STRATEGY COMPARISON USING ML OPTIMIZATION")
        print(f"{'='*80}")
        
        results = {}
        
        for strategy in strategies:
            print(f"\nOptimizing {strategy}...")
            
            try:
                result = self.optimize_strategy(
                    strategy_name=strategy,
                    symbols=symbols,
                    optimizer_type=optimizer_type,
                    objective_function=objective_function,
                    max_evaluations=max_evaluations_per_strategy,
                    save_results=False  # Don't save individual results
                )
                
                results[strategy] = result
                
            except Exception as e:
                print(f"Error optimizing {strategy}: {e}")
                continue
        
        # Print comparison summary
        print_strategy_comparison(results, objective_function)
        
        return results
    
    def run_walk_forward_optimization(self,
                                    strategy_name: str,
                                    symbols: List[str],
                                    training_window_months: int = 12,
                                    reoptimization_frequency_months: int = 3,
                                    optimizer_type: str = 'bayesian',
                                    objective_function: str = 'sharpe_ratio',
                                    max_evaluations: int = 50) -> Dict[str, Any]:
        """
        Run walk-forward optimization to test parameter stability
        
        Args:
            strategy_name: Strategy to optimize
            symbols: List of symbols to test on
            training_window_months: Training window in months
            reoptimization_frequency_months: How often to reoptimize
            optimizer_type: Type of optimizer
            objective_function: Objective function
            max_evaluations: Max evaluations per period
            
        Returns:
            Walk-forward optimization results
        """
        print(f"\n{'='*80}")
        print(f"WALK-FORWARD OPTIMIZATION")
        print(f"{'='*80}")
        print(f"Strategy: {strategy_name}")
        print(f"Training Window: {training_window_months} months")
        print(f"Reoptimization Frequency: {reoptimization_frequency_months} months")
        
        # Calculate date ranges for walk-forward
        end_date = datetime.now()
        total_period_months = 24  # 2 years total
        
        periods = []
        current_end = end_date
        
        while len(periods) * reoptimization_frequency_months < total_period_months:
            train_start = current_end - timedelta(days=training_window_months * 30)
            train_end = current_end - timedelta(days=reoptimization_frequency_months * 30)
            test_start = train_end
            test_end = current_end
            
            periods.append({
                'train_start': train_start.strftime('%Y-%m-%d'),
                'train_end': train_end.strftime('%Y-%m-%d'),
                'test_start': test_start.strftime('%Y-%m-%d'),
                'test_end': test_end.strftime('%Y-%m-%d')
            })
            
            current_end = test_start
        
        periods.reverse()  # Chronological order
        
        results = []
        
        for i, period in enumerate(periods):
            print(f"\nPeriod {i+1}/{len(periods)}")
            print(f"Training: {period['train_start']} to {period['train_end']}")
            print(f"Testing: {period['test_start']} to {period['test_end']}")
            
            try:
                # Optimize on training data
                optimization_result = self.optimize_strategy(
                    strategy_name=strategy_name,
                    symbols=symbols,
                    start_date=period['train_start'],
                    end_date=period['train_end'],
                    optimizer_type=optimizer_type,
                    objective_function=objective_function,
                    max_evaluations=max_evaluations,
                    save_results=False
                )
                
                # Test on out-of-sample data
                test_data = self._load_historical_data(
                    symbols, period['test_start'], period['test_end']
                )
                
                if test_data:
                    test_result = self.backtest_wrapper(
                        strategy_name=strategy_name,
                        parameters=optimization_result['best_parameters'],
                        historical_data=test_data
                    )
                    
                    period_result = {
                        'period': i + 1,
                        'train_period': f"{period['train_start']} to {period['train_end']}",
                        'test_period': f"{period['test_start']} to {period['test_end']}",
                        'optimal_parameters': optimization_result['best_parameters'],
                        'training_objective': optimization_result['best_objective_value'],
                        'test_performance': extract_metrics_from_backtest(test_result),
                        'parameter_stability': self._calculate_parameter_stability(
                            optimization_result['best_parameters'], results
                        )
                    }
                    
                    results.append(period_result)
                
            except Exception as e:
                print(f"Error in period {i+1}: {e}")
                continue
        
        # Calculate overall walk-forward statistics
        walk_forward_summary = self._summarize_walk_forward_results(results)
        
        print(f"\n{'='*80}")
        print(f"WALK-FORWARD OPTIMIZATION COMPLETED")
        print(f"{'='*80}")
        
        return {
            'strategy_name': strategy_name,
            'walk_forward_config': {
                'training_window_months': training_window_months,
                'reoptimization_frequency_months': reoptimization_frequency_months,
                'total_periods': len(results)
            },
            'period_results': results,
            'summary_statistics': walk_forward_summary
        }
    
    def _load_historical_data(self, symbols: List[str], start_date: str, end_date: str) -> Dict[str, Any]:
        """Load historical data for optimization using direct Kite API calls"""
        historical_data = {}
        
        # Calculate days back from the date range
        from datetime import datetime
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        days_back = (end_dt - start_dt).days
        
        for symbol in symbols:
            try:
                # Get instrument token
                instrument_token = get_instrument_token(symbol)
                
                # Fetch data using direct Kite API
                data = fetch_historical_data(
                    kite=self.kite,
                    symbol=symbol,
                    instrument_token=instrument_token,
                    days_back=days_back,
                    interval="15minute"
                )
                
                if data is not None and not data.empty:
                    historical_data[symbol] = data
                    print(f"✅ Loaded {len(data)} rows for {symbol}")
                else:
                    print(f"⚠️  Warning: No data available for {symbol}")
                    
            except Exception as e:
                print(f"❌ Error loading data for {symbol}: {e}")
                continue
        
        return historical_data
    
    def _print_optimization_summary(self, results: Dict[str, Any]):
        """Print optimization summary"""
        print(f"\n{'='*80}")
        print(f"OPTIMIZATION SUMMARY")
        print(f"{'='*80}")
        print(f"Strategy: {results['strategy_name']}")
        print(f"Optimizer: {results['optimizer_type']}")
        print(f"Objective Function: {results['objective_function']}")
        print(f"\nBest Parameters:")
        for param, value in results['best_parameters'].items():
            print(f"  {param}: {value}")
        print(f"\nBest Objective Value: {results['best_objective_value']:.4f}")
        print(f"\nKey Metrics:")
        for metric, value in results['best_metrics'].items():
            if isinstance(value, (int, float)):
                print(f"  {metric}: {value:.4f}")
            else:
                print(f"  {metric}: {value}")
        print(f"{'='*80}")
    
    def _print_strategy_comparison(self, results: Dict[str, Any], objective: str):
        """Print strategy comparison results"""
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
    
    def _extract_test_metrics(self, test_result: Dict[str, Any]) -> Dict[str, float]:
        """Extract metrics from test backtest results"""
        if not test_result or 'performance_metrics' not in test_result:
            return {}
        
        performance = test_result['performance_metrics']
        metrics = {}
        
        metric_names = [
            'total_return', 'annualized_return', 'volatility', 'sharpe_ratio',
            'max_drawdown', 'win_rate', 'calmar_ratio'
        ]
        
        for metric in metric_names:
            value = getattr(performance, metric, None)
            if value is not None:
                metrics[metric] = float(value)
        
        return metrics
    
    def _calculate_parameter_stability(self, current_params: Dict[str, Any], 
                                     previous_results: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate parameter stability metrics"""
        if not previous_results:
            return {'stability_score': 1.0}
        
        # Get previous parameters
        prev_params = previous_results[-1]['optimal_parameters']
        
        # Calculate parameter differences
        stability_scores = []
        
        for param_name, current_value in current_params.items():
            if param_name in prev_params:
                prev_value = prev_params[param_name]
                
                if isinstance(current_value, (int, float)) and isinstance(prev_value, (int, float)):
                    # Normalized difference for numeric parameters
                    param_space = ParameterSpace.get_strategy_space(
                        previous_results[0].get('strategy_name', 'moving_average_crossover')
                    )
                    
                    if param_name in param_space:
                        spec = param_space[param_name]
                        if spec.param_type in ['int', 'float']:
                            min_val, max_val = spec.bounds
                            param_range = max_val - min_val
                            if param_range > 0:
                                diff = abs(current_value - prev_value) / param_range
                                stability_scores.append(1.0 - diff)
                else:
                    # Categorical parameters
                    stability_scores.append(1.0 if current_value == prev_value else 0.0)
        
        overall_stability = sum(stability_scores) / len(stability_scores) if stability_scores else 1.0
        
        return {
            'stability_score': overall_stability,
            'parameter_changes': len([s for s in stability_scores if s < 1.0])
        }
    
    def _summarize_walk_forward_results(self, results: List[Dict[str, Any]]) -> Dict[str, float]:
        """Summarize walk-forward optimization results"""
        if not results:
            return {}
        
        # Extract test performance metrics
        test_returns = []
        test_sharpes = []
        stability_scores = []
        
        for result in results:
            test_perf = result.get('test_performance', {})
            if 'total_return' in test_perf:
                test_returns.append(test_perf['total_return'])
            if 'sharpe_ratio' in test_perf:
                test_sharpes.append(test_perf['sharpe_ratio'])
            
            stability = result.get('parameter_stability', {})
            if 'stability_score' in stability:
                stability_scores.append(stability['stability_score'])
        
        summary = {}
        
        if test_returns:
            summary['avg_test_return'] = sum(test_returns) / len(test_returns)
            summary['std_test_return'] = (sum((r - summary['avg_test_return'])**2 for r in test_returns) / len(test_returns))**0.5
        
        if test_sharpes:
            summary['avg_test_sharpe'] = sum(test_sharpes) / len(test_sharpes)
            summary['std_test_sharpe'] = (sum((s - summary['avg_test_sharpe'])**2 for s in test_sharpes) / len(test_sharpes))**0.5
        
        if stability_scores:
            summary['avg_parameter_stability'] = sum(stability_scores) / len(stability_scores)
        
        summary['total_periods'] = len(results)
        summary['successful_periods'] = len([r for r in results if r.get('test_performance')])
        
        return summary

def main():
    """Example usage of ML optimization interface"""
    
    # Initialize the interface
    ml_optimizer = MLOptimizationInterface()
    
    # Example 1: Single strategy optimization
    print("Example 1: Single Strategy Optimization")
    try:
        result = ml_optimizer.optimize_strategy(
            strategy_name='moving_average_crossover',
            symbols=['NIFTY50'],
            optimizer_type='grid_search',  # Start with grid search (most reliable)
            objective_function='sharpe_ratio',
            max_evaluations=20  # Small number for testing
        )
        print("Single strategy optimization completed successfully!")
        
    except Exception as e:
        print(f"Error in single strategy optimization: {e}")
    
    # Example 2: Strategy comparison
    print("\nExample 2: Strategy Comparison")
    try:
        comparison_results = ml_optimizer.compare_strategies(
            strategies=['moving_average_crossover', 'rsi_mean_reversion'],
            symbols=['NIFTY50'],
            optimizer_type='grid_search',
            max_evaluations_per_strategy=15
        )
        print("Strategy comparison completed successfully!")
        
    except Exception as e:
        print(f"Error in strategy comparison: {e}")

if __name__ == "__main__":
    main()