class MarketDataConfig:
    SYMBOLS = [
  "SBIN"
]


    EXCHANGE = "NSE"
    INTERVAL = "5minute"
    LOOKBACK_DAYS = 30
    
    FETCH_INTERVAL = "1min"
    SIGNAL_INTERVAL = "5min"
    USE_RESAMPLING = True
    
    INTERVALS = {
        '1min': 'minute',
        '5min': '5minute',
        '15min': '15minute',
        '1hour': '60minute',
        '1day': 'day'
    }


class BacktestConfig:
    INITIAL_CAPITAL = 100000.0
    COMMISSION_RATE = 0.003
    POSITION_SIZE = 10000.0


class StrategyConfig:
    DEFAULT_STRATEGY = "VWAP_REVERSION"
    
    MA_CROSSOVER = {
        'fast_period': 5,
        'slow_period': 8
    }
    
    RSI = {
        'rsi_period': 14,
        'oversold': 30,
        'overbought': 65,
        'min_confidence': 0.7
    }
    
    BOLLINGER = {
        'bb_period': 20,
        'bb_std': 2,
        'min_confidence': 0.7
    }
    
    ORB_VWAP = {
        'orb_minutes': 15,
        'rvol_threshold': 1.5,
        'vwap_distance_atr': 1.5,
        'stop_atr_mult': 0.6,
        'trail_atr_mult': 2.0,
        'gap_min': 0.5,
        'gap_max': 3.0,
        'atr_period': 14,
        'min_confidence': 0.7
    }
    
    VWAP_REVERSION = {
        'min_time': '10:00',
        'rvol_threshold': 2.0,
        'extension_atr_mult': 2.0,
        'vwap_reclaim_sd': 0.5,
        'atr_period': 14,
        'lookback_bars': 3,
        'min_confidence': 0.7,
        'rvol_lookback': 20
    }

