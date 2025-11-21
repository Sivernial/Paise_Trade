class MarketDataConfig:
    # NIFTY 50 stocks + NIFTY 50 index for market filter
    SYMBOLS = [
  "SBIN", "NIFTY 50"
]


    EXCHANGE = "NSE"
    INTERVAL = "5minute"
    LOOKBACK_DAYS = 30
    
    FETCH_INTERVAL = "5min"
    SIGNAL_INTERVAL = "15min"
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
    POSITION_SIZE = 5000.0


class StrategyConfig:
    DEFAULT_STRATEGY = "MA_CROSSOVER"
    
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
    
    # Hybrid ORB/VWAP Strategy - Full Position Management
    # PRIMARY: ORB/VWAP Momentum (Longs Only)
    # Entry: After 9:30 when 5-min close breaks ORH, above VWAP, RVOL > 1.5
    # Stop: max(ORH - 0.6*ATR, VWAP - 1.0*ATR)
    # Target: Scale 50% at +1R, trail rest with 2*ATR Chandelier
    # Market Filter: NIFTY above 20-EMA or VWAP
    # Time Stop: Flat by 15:20
    HYBRID_ORB = {
        # ORB Parameters
        'orb_minutes': 15,
        'orb_start_time': '09:15',
        'entry_start_time': '09:30',
        'time_stop': '15:20',
        
        # Entry Filters
        'rvol_threshold': 1.5,
        'vwap_distance_atr': 1.5,
        
        # Risk Management
        'atr_period': 5,  # 5-period ATR for 5-min bars
        'stop_orb_atr_mult': 0.6,
        'stop_vwap_atr_mult': 1.0,
        'trail_atr_mult': 2.0,
        
        # Position Management
        'partial_exit_r': 1.0,
        'partial_exit_pct': 0.5,
        'use_chandelier_trail': True,
        
        # Market Filter
        'use_market_filter': True,
        'market_index': 'NIFTY 50',
        'ema_period': 20,
        
        # Mode Control
        'enable_longs': True,
        'enable_shorts': False,
        'enable_reversion': False,
        
        # RVOL
        'rvol_lookback': 20
    }

