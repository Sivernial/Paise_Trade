"""
Parameter Spaces for Strategy Optimization
Defines the search spaces for each trading strategy's parameters.
Each parameter has bounds, type, and default value for optimization algorithms.
"""
from typing import Dict, Any, List, Tuple, Union
from .constants import ParameterSpec
class ParameterSpace:
    """Defines the parameter search space for strategy optimization"""
    # Moving Average Crossover Strategy Parameters
    MA_CROSSOVER_SPACE = {
        'fast_period': ParameterSpec(
            param_type='int',
            bounds=(5, 50),
            default=10,
            description='Fast moving average period'
        ),
        'slow_period': ParameterSpec(
            param_type='int',
            bounds=(20, 200),
            default=50,
            description='Slow moving average period'
        ),
        'min_confidence': ParameterSpec(
            param_type='float',
            bounds=(0.5, 0.95),
            default=0.7,
            description='Minimum signal confidence threshold'
        )
    }
    # RSI Mean Reversion Strategy Parameters
    RSI_MEAN_REVERSION_SPACE = {
        'rsi_period': ParameterSpec(
            param_type='int',
            bounds=(5, 30),
            default=14,
            description='RSI calculation period'
        ),
        'oversold_threshold': ParameterSpec(
            param_type='float',
            bounds=(20, 40),
            default=30,
            description='RSI oversold threshold for buy signals'
        ),
        'overbought_threshold': ParameterSpec(
            param_type='float',
            bounds=(60, 80),
            default=70,
            description='RSI overbought threshold for sell signals'
        ),
        'min_confidence': ParameterSpec(
            param_type='float',
            bounds=(0.5, 0.95),
            default=0.6,
            description='Minimum signal confidence threshold'
        )
    }
    # Bollinger Band Strategy Parameters
    BOLLINGER_BAND_SPACE = {
        'bb_period': ParameterSpec(
            param_type='int',
            bounds=(10, 50),
            default=20,
            description='Bollinger Band period'
        ),
        'bb_std': ParameterSpec(
            param_type='float',
            bounds=(1.0, 3.0),
            default=2.0,
            description='Bollinger Band standard deviation multiplier'
        ),
        'strategy_type': ParameterSpec(
            param_type='categorical',
            bounds=['reversal', 'breakout', 'squeeze', 'adaptive'],
            default='reversal',
            description='Bollinger Band strategy type'
        ),
        'min_confidence': ParameterSpec(
            param_type='float',
            bounds=(0.5, 0.95),
            default=0.65,
            description='Minimum signal confidence threshold'
        )
    }
    # Multi-Indicator Strategy Parameters
    MULTI_INDICATOR_SPACE = {
        'ma_fast': ParameterSpec(
            param_type='int',
            bounds=(5, 30),
            default=10,
            description='Fast moving average period'
        ),
        'ma_slow': ParameterSpec(
            param_type='int',
            bounds=(20, 100),
            default=30,
            description='Slow moving average period'
        ),
        'rsi_period': ParameterSpec(
            param_type='int',
            bounds=(10, 25),
            default=14,
            description='RSI period for momentum filter'
        ),
        'bb_period': ParameterSpec(
            param_type='int',
            bounds=(15, 40),
            default=20,
            description='Bollinger Band period'
        ),
        'min_confidence': ParameterSpec(
            param_type='float',
            bounds=(0.6, 0.95),
            default=0.8,
            description='Minimum signal confidence threshold'
        )
    }
    # Adaptive Momentum Breakout Strategy Parameters
    ADAPTIVE_MOMENTUM_SPACE = {
        'min_confidence': ParameterSpec(
            param_type='float',
            bounds=(0.5, 0.9),
            default=0.65,
            description='Minimum confidence threshold'
        ),
        'vwap_deviation_threshold': ParameterSpec(
            param_type='float',
            bounds=(0.002, 0.02),
            default=0.008,
            description='VWAP deviation threshold for signals'
        ),
        'supertrend_multiplier': ParameterSpec(
            param_type='float',
            bounds=(1.5, 4.0),
            default=2.5,
            description='SuperTrend ATR multiplier'
        ),
        'rsi_oversold': ParameterSpec(
            param_type='float',
            bounds=(25, 45),
            default=35,
            description='RSI oversold threshold'
        ),
        'rsi_overbought': ParameterSpec(
            param_type='float',
            bounds=(55, 75),
            default=65,
            description='RSI overbought threshold'
        ),
        'atr_multiplier': ParameterSpec(
            param_type='float',
            bounds=(1.0, 3.5),
            default=2.0,
            description='ATR risk multiplier'
        ),
        'volume_spike_threshold': ParameterSpec(
            param_type='float',
            bounds=(1.1, 2.0),
            default=1.3,
            description='Volume spike detection threshold'
        )
    }
    # Backtesting Parameters (common to all strategies)
    BACKTESTING_SPACE = {
        'initial_capital': ParameterSpec(
            param_type='float',
            bounds=(50000, 500000),
            default=100000,
            description='Initial trading capital'
        ),
        'commission_rate': ParameterSpec(
            param_type='float',
            bounds=(0.0001, 0.01),
            default=0.001,
            description='Commission rate per trade'
        ),
        'slippage_rate': ParameterSpec(
            param_type='float',
            bounds=(0.0001, 0.005),
            default=0.0005,
            description='Slippage rate per trade'
        ),
        'position_size_pct': ParameterSpec(
            param_type='float',
            bounds=(0.1, 1.0),
            default=0.5,
            description='Position size as percentage of portfolio'
        )
    }
    @classmethod
    def get_strategy_space(cls, strategy_name: str) -> Dict[str, ParameterSpec]:
        """Get parameter space for a specific strategy"""
        strategy_spaces = {
            'MovingAverageCrossoverStrategy': cls.MA_CROSSOVER_SPACE,
            'RSIMeanReversionStrategy': cls.RSI_MEAN_REVERSION_SPACE,
            'BollingerBandStrategy': cls.BOLLINGER_BAND_SPACE,
            'MultiIndicatorStrategy': cls.MULTI_INDICATOR_SPACE,
            'AdaptiveMomentumBreakoutStrategy': cls.ADAPTIVE_MOMENTUM_SPACE
        }
        strategy_space = strategy_spaces.get(strategy_name, {})
        # Always include backtesting parameters
        combined_space = {**strategy_space, **cls.BACKTESTING_SPACE}
        return combined_space
    @classmethod
    def get_bounds_for_optimizer(cls, strategy_name: str, include_backtesting: bool = True) -> Dict[str, Union[Tuple, List]]:
        """Get parameter bounds in format suitable for optimization algorithms"""
        space = cls.get_strategy_space(strategy_name)
        if not include_backtesting:
            # Filter out backtesting parameters
            backtesting_params = set(cls.BACKTESTING_SPACE.keys())
            space = {k: v for k, v in space.items() if k not in backtesting_params}
        bounds = {}
        for name, spec in space.items():
            bounds[name] = spec.bounds
        return bounds
    @classmethod
    def get_default_params(cls, strategy_name: str) -> Dict[str, Any]:
        """Get default parameter values for a strategy"""
        space = cls.get_strategy_space(strategy_name)
        return {name: spec.default for name, spec in space.items()}
    @classmethod
    def validate_parameters(cls, strategy_name: str, params: Dict[str, Any]) -> bool:
        """Validate parameter values against defined space"""
        space = cls.get_strategy_space(strategy_name)
        for name, value in params.items():
            if name not in space:
                continue
            spec = space[name]
            if spec.param_type in ['int', 'float']:
                min_val, max_val = spec.bounds
                if not (min_val <= value <= max_val):
                    return False
            elif spec.param_type == 'categorical':
                if value not in spec.bounds:
                    return False
            elif spec.param_type == 'bool':
                if not isinstance(value, bool):
                    return False
        return True
    
    @classmethod
    def get_strategy_names(cls) -> List[str]:
        """Get list of all available strategy names"""
        return [
            'moving_average_crossover',
            'rsi_mean_reversion', 
            'bollinger_band',
            'multi_indicator',
            'adaptive_momentum_breakout'
        ]
    
    @classmethod
    def validate_parameters(cls, strategy_name: str, parameters: Dict[str, Any]) -> bool:
        """
        Validate that parameters are within bounds
        
        Args:
            strategy_name: Name of the strategy
            parameters: Parameter values to validate
            
        Returns:
            True if all parameters are valid
        """
        space = cls.get_strategy_space(strategy_name)
        
        for param_name, value in parameters.items():
            if param_name not in space:
                continue  # Skip unknown parameters
            
            spec = space[param_name]
            
            if spec.param_type in ['int', 'float']:
                min_val, max_val = spec.bounds
                if not (min_val <= value <= max_val):
                    print(f"Parameter {param_name} = {value} is outside bounds ({min_val}, {max_val})")
                    return False
            
            elif spec.param_type == 'categorical':
                if value not in spec.bounds:
                    print(f"Parameter {param_name} = {value} is not in allowed values {spec.bounds}")
                    return False
                    
            elif spec.param_type == 'bool':
                if not isinstance(value, bool):
                    print(f"Parameter {param_name} = {value} should be boolean")
                    return False
        
        return True