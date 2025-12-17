class MarketDataConfig:
    # NIFTY 50 stocks + NIFTY 50 index for market filter
    SYMBOLS = [
        "ACC", "AMBUJACEM",
        "TMPV", "M&M",
        "SBIN", "PNB",
        "INFY", "TCS",
        "HDFCBANK",
        "NIFTY 50"  # ✅ Market index for filter
    ]


    EXCHANGE = "NSE"
    INDEX_EXCHANGE = "NSE"  # Some brokers use "NSE" or "INDICES" for index data
    INTERVAL = "5minute"
    LOOKBACK_DAYS = 40 # Tuned for balance
    
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
    POSITION_SIZE = 5000.0
    
    # ===== INDIAN MARKET COST MODEL =====
    # Based on NSE Equity Intraday Trading (Discount Brokers like Zerodha)
    
    # Brokerage: Flat ₹20 per order or 0.03% (whichever is lower)
    BROKERAGE_FLAT = 20.0
    BROKERAGE_PERCENTAGE = 0.0003
    
    # STT (Securities Transaction Tax): 0.025% on SELL side only for intraday
    STT_RATE_SELL = 0.00025
    
    # NSE Transaction Charges: 0.00325% of turnover
    TRANSACTION_CHARGES_RATE = 0.0000325
    
    # GST: 18% on (Brokerage + Transaction Charges)
    GST_RATE = 0.18
    
    # SEBI Charges: ₹10 per crore (0.0001%)
    SEBI_CHARGES_RATE = 0.000001
    
    # Stamp Duty: 0.003% on BUY side only
    STAMP_DUTY_RATE = 0.00003
    
    # Slippage: Expected slippage per trade (5 bps)
    SLIPPAGE_BPS = 5
    SLIPPAGE_RATE = 0.0005
    
    # ===== SIMPLIFIED COMBINED RATE =====
    # Conservative estimate for quick calculations (~0.05% total)
    # Includes: Brokerage + STT + Transaction charges + GST + SEBI + Stamp Duty
    COMMISSION_RATE = 0.0005


class PortfolioConfig:
    RISK_FREE_RATE = 0.06 # India 10Y Bond Approx
    MAX_ASSET_WEIGHT = 0.4 # Max 40% in one pair
    MIN_ASSET_WEIGHT = 0.05 # Min 5%
    REBALANCE_DAYS = 30


class StrategyConfig:
    DEFAULT_STRATEGY = "PAIR_TRADING"
    
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

    PAIR_TRADING = {
        'pairs': [
            ('ACC', 'AMBUJACEM'),      # Cement
            ('TATAMOTORS', 'M&M'),     # Auto
            ('SBIN', 'PNB'),           # PSU Banks
            ('INFY', 'TCS')            # IT
        ],
        'z_score_threshold': 2.0,
        'lookback_window': 40, # Balance between noise and lag
        'stop_loss_z': 4.0,  # Stop if spread diverges too much
        'take_profit_z': 0.0, # Exit at mean
        'min_confidence': 0.8,
        'time_stop': None  # Disable intraday time stop for multi-day holding
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


def calculate_indian_transaction_cost(quantity: int, price: float, is_buy: bool) -> dict:

    turnover = quantity * price
    
    # 1. Brokerage (₹20 flat or 0.03%, whichever is lower)
    brokerage = min(BacktestConfig.BROKERAGE_FLAT, 
                   turnover * BacktestConfig.BROKERAGE_PERCENTAGE)
    
    # 2. STT (only on SELL for intraday)
    stt = turnover * BacktestConfig.STT_RATE_SELL if not is_buy else 0.0
    
    # 3. Transaction charges
    txn_charges = turnover * BacktestConfig.TRANSACTION_CHARGES_RATE
    
    # 4. GST (18% on brokerage + transaction charges)
    gst = (brokerage + txn_charges) * BacktestConfig.GST_RATE
    
    # 5. SEBI charges
    sebi = turnover * BacktestConfig.SEBI_CHARGES_RATE
    
    # 6. Stamp duty (only on BUY)
    stamp = turnover * BacktestConfig.STAMP_DUTY_RATE if is_buy else 0.0
    
    total_cost = brokerage + stt + txn_charges + gst + sebi + stamp
    
    return {
        'turnover': turnover,
        'brokerage': brokerage,
        'stt': stt,
        'transaction_charges': txn_charges,
        'gst': gst,
        'sebi_charges': sebi,
        'stamp_duty': stamp,
        'total_cost': total_cost,
        'cost_percentage': (total_cost / turnover * 100) if turnover > 0 else 0.0
    }

