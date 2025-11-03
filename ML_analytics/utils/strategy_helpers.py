"""
Strategy Helper Functions

Contains functions for creating and managing strategy instances
for ML optimization backtesting.
"""

from typing import Dict, Any
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from data_structures.common import OrderType

# Import strategy classes
from strategies import (
    MovingAverageCrossoverStrategy, 
    RSIMeanReversionStrategy, 
    BollingerBandStrategy,
    MultiIndicatorStrategy
)
from strategies.adaptive_momentum_breakout import AdaptiveMomentumBreakoutStrategy


def get_strategy_class(strategy_name: str):
    """
    Get strategy class by name
    
    Args:
        strategy_name: Name of the strategy
        
    Returns:
        Strategy class
    """
    strategy_mapping = {
        'moving_average_crossover': MovingAverageCrossoverStrategy,
        'rsi_mean_reversion': RSIMeanReversionStrategy,
        'bollinger_band': BollingerBandStrategy,
        'multi_indicator': MultiIndicatorStrategy,
        'adaptive_momentum_breakout': AdaptiveMomentumBreakoutStrategy
    }
    
    if strategy_name not in strategy_mapping:
        raise ValueError(f"Unknown strategy: {strategy_name}. Available: {list(strategy_mapping.keys())}")
    
    return strategy_mapping[strategy_name]


def create_strategy_function(strategy_name: str, strategy_params: Dict[str, Any], position_size_pct: float = 0.5):
    """
    Create strategy function for backtesting based on strategy name and parameters
    
    Args:
        strategy_name: Name of the strategy
        strategy_params: Strategy parameters
        position_size_pct: Position size as percentage of portfolio
    
    Returns:
        Strategy function compatible with BacktestEngine
    """
    
    # Get strategy class
    strategy_class = get_strategy_class(strategy_name)
    
    # Initialize the strategy with parameters
    strategy = strategy_class(params=strategy_params)
    
    def generic_backtest_function(data_dict, backtest_engine, current_date):
        """
        Generic strategy function for backtesting any strategy
        """
        
        # Generate signals using the strategy
        signals = strategy.generate_signals(data_dict, current_date)
        
        for signal in signals:
            symbol = signal.symbol
            current_price = signal.price
            portfolio_value = backtest_engine.get_portfolio_value()
            
            # Check current position
            has_position = symbol in backtest_engine.positions
            
            if signal.signal_type.value == 'BUY' and not has_position:
                # Calculate position size
                position_value = portfolio_value * position_size_pct
                quantity = int(position_value / current_price)
                
                if quantity > 0:
                    backtest_engine.place_order(
                        symbol=symbol,
                        quantity=quantity,
                        order_type=OrderType.BUY,
                        price=current_price
                    )
            
            elif signal.signal_type.value == 'SELL' and has_position:
                position = backtest_engine.positions[symbol]
                backtest_engine.place_order(
                    symbol=symbol,
                    quantity=position.quantity,
                    order_type=OrderType.SELL,
                    price=current_price
                )
    
    return generic_backtest_function