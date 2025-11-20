class MarketDataConfig:
    SYMBOLS = ['RELIANCE','HDFCBANK']
    EXCHANGE = "NSE"
    INTERVAL = "5minute"
    LOOKBACK_DAYS = 100
    
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
    DEFAULT_STRATEGY = "MACrossover"
    
    MA_CROSSOVER = {
        'fast_period': 5,
        'slow_period': 8
    }

