DYNAMIC_INDICATOR_CONFIGS = {
    'volatility': {
        'period': 20,
        'annualize': True
    },
    'momentum': {
        'period': 10
    },
    'trend_strength': {
        'short_period': 10,
        'long_period': 50
    },
    'volume_profile': {
        'period': 20,
        'threshold': 1.5
    },
    'support_resistance': {
        'lookback': 50,
        'num_levels': 3
    },
    'volatility_ratio': {
        'short_period': 10,
        'long_period': 30
    },
    'price_channels': {
        'period': 20
    }
}

def get_config(indicator_name: str) -> dict:
    return DYNAMIC_INDICATOR_CONFIGS.get(indicator_name, {})

def update_config(indicator_name: str, config: dict):
    if indicator_name in DYNAMIC_INDICATOR_CONFIGS:
        DYNAMIC_INDICATOR_CONFIGS[indicator_name].update(config)

