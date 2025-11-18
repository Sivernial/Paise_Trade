"""
Backtest Wrapper Functions

Contains the main backtest wrapper and related functions for 
integrating with optimization algorithms.
"""

from typing import Dict, Any
from .strategy_helpers import create_strategy_function


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
            parameters: Strategy parameters (includes both strategy and backtest parameters)
            historical_data: Historical price data
            
        Returns:
            Backtest results dictionary
        """
        try:
            # Separate strategy parameters from backtest engine parameters
            strategy_params = {}
            backtest_params = {}
            position_size_pct = 0.5  # default
            
            for key, value in parameters.items():
                if key in ['initial_capital', 'commission_rate', 'slippage_rate']:
                    backtest_params[key] = value
                elif key == 'position_size_pct':
                    position_size_pct = value
                else:
                    # This should be a strategy-specific parameter
                    strategy_params[key] = value
            
            # Update backtest engine parameters if provided
            if 'initial_capital' in backtest_params:
                backtest_engine.initial_capital = backtest_params['initial_capital']
                backtest_engine.cash = backtest_params['initial_capital']
            if 'commission_rate' in backtest_params:
                backtest_engine.commission_rate = backtest_params['commission_rate']
            if 'slippage_rate' in backtest_params:
                backtest_engine.slippage_rate = backtest_params['slippage_rate']
            
            # Create strategy function with the strategy-specific parameters
            strategy_function = create_strategy_function(
                strategy_name=strategy_name,
                strategy_params=strategy_params,
                position_size_pct=position_size_pct
            )
            
            # Set the strategy function
            backtest_engine.set_strategy(strategy_function)
            
            # Run backtest with the data
            results = backtest_engine.run_backtest(
                data=historical_data,
                generate_plots=False  # No plots during optimization
            )
            
            return results
            
        except Exception as e:
            print(f"Error in backtest wrapper: {e}")
            return {'performance_metrics': None}
    
    return backtest_wrapper