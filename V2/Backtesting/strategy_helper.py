from .config import StrategyConfig
from Algorithms import MACrossoverStrategy


def get_strategy_params(strategy_name: str) -> dict:
    strategy_map = {
        'MACrossover': StrategyConfig.MA_CROSSOVER,
    }
    return strategy_map.get(strategy_name, {})


def get_strategy_instance(strategy_name: str = None):
    if strategy_name is None:
        strategy_name = StrategyConfig.DEFAULT_STRATEGY
    
    strategy_classes = {
        'MACrossover': MACrossoverStrategy,
    }
    
    strategy_class = strategy_classes.get(strategy_name)
    if not strategy_class:
        raise ValueError(f"Unknown strategy: {strategy_name}")
    
    params = get_strategy_params(strategy_name)
    return strategy_class(params)

