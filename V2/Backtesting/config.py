class MarketDataConfig:
    SYMBOLS = [
  "ETERNAL", "WIPRO", "HDFCBANK", "TATASTEEL", "ITC",
  "BEL", "RELIANCE", "ICICIBANK", "INFY",
  "POWERGRID", "ONGC", "JIOFIN", "SBIN"
]


    EXCHANGE = "NSE"
    INTERVAL = "5minute"
    LOOKBACK_DAYS = 30
    
    INTERVALS = {
        '1min': 'minute',
        '5min': '5minute',
        '15min': '15minute',
        '1hour': '60minute',
        '1day': 'day'
    }


class BacktestConfig:
    INITIAL_CAPITAL = 1000000.0
    COMMISSION_RATE = 0.003
    POSITION_SIZE = 1000.0


class StrategyConfig:
    DEFAULT_STRATEGY = "RSI"
    
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

