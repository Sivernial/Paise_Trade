"""
Trading Strategies Module

This module contains all trading strategies organized for easy import and use.

Available Strategies:
1. BaseStrategy - Abstract base class for all strategies
2. MovingAverageCrossoverStrategy - Simple MA crossover signals
3. RSIMeanReversionStrategy - RSI-based mean reversion
4. BollingerBandStrategy - Bollinger Band multi-mode strategy
5. MultiIndicatorStrategy - Combined indicators approach

Usage:
    from strategies import MovingAverageCrossoverStrategy
    
    strategy = MovingAverageCrossoverStrategy(
        params={'fast_period': 10, 'slow_period': 20}
    )
"""

from .base_strategy import BaseStrategy
from .moving_average_crossover import MovingAverageCrossoverStrategy
from .rsi_mean_reversion import RSIMeanReversionStrategy
from .bollinger_band import BollingerBandStrategy
from .multi_indicator import MultiIndicatorStrategy

__all__ = [
    'BaseStrategy',
    'MovingAverageCrossoverStrategy',
    'RSIMeanReversionStrategy', 
    'BollingerBandStrategy',
    'MultiIndicatorStrategy'
]

# Strategy registry for easy access
STRATEGY_REGISTRY = {
    'ma_crossover': MovingAverageCrossoverStrategy,
    'rsi_mean_reversion': RSIMeanReversionStrategy,
    'bollinger_band': BollingerBandStrategy,
    'multi_indicator': MultiIndicatorStrategy
}

def get_strategy(strategy_name: str, **kwargs):
    """
    Factory function to get strategy by name
    
    Args:
        strategy_name: Name of the strategy
        **kwargs: Strategy parameters
        
    Returns:
        Strategy instance
    """
    if strategy_name not in STRATEGY_REGISTRY:
        raise ValueError(f"Unknown strategy: {strategy_name}. Available: {list(STRATEGY_REGISTRY.keys())}")
    
    strategy_class = STRATEGY_REGISTRY[strategy_name]
    return strategy_class(**kwargs)

def list_strategies():
    """List all available strategies"""
    return list(STRATEGY_REGISTRY.keys())