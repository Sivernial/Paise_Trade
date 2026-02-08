
# 3-Timeframe MTFA Configuration
# UPDATED: Jan 29, 2026 - V7.2 ADAPTIVE CONFIGURATION
# Standardized on ATR-based Targets, Stops, and Overextension Guards

CONFIG = {
    # === THE V3 VOLATILITY KINGS (Optimized for 4%+ ATR) ===
    
    # 1. ADANI GREEN (Ultra-High Volatility)
    "ADANIGREEN": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "use_atr_target": True, "atr_multiplier": 3.0,
            "use_atr_sl": True, "atr_sl_multiplier": 2.5,
            "trailing_type": "chandelier", "chandelier_multiplier": 3.0,
            "max_ema_dist_atr": 1.2, "adx_min": 30, "max_atr_allowed": 0.08,
            "leverage": 4.0, "max_capital": 30000, "opening_noise_mins": 5,
            # V8 Features
            "gap_tolerance_pct": 0.005, "use_market_depth": True,
            "partial_exit_atr": 1.2, "partial_qty_pct": 0.5,
            "correlated_index": "NIFTY"
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # 2. ETERNAL (ZOMATO - Momentum Play)
    "ETERNAL": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "use_atr_target": True, "atr_multiplier": 2.0,
            "use_atr_sl": True, "atr_sl_multiplier": 1.5,
            "max_ema_dist_atr": 1.5, "adx_min": 25, "max_atr_allowed": 0.05,
            "leverage": 4.0, "max_capital": 20000, "opening_noise_mins": 5,
            "correlated_index": "NIFTY"
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # 3. ADANI ENSOL
    "ADANIENSOL": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "use_atr_target": True, "atr_multiplier": 2.5,
            "use_atr_sl": True, "atr_sl_multiplier": 2.0,
            "max_ema_dist_atr": 1.3, "adx_min": 28, "max_atr_allowed": 0.06,
            "leverage": 4.0, "max_capital": 100000, "opening_noise_mins": 5,
            "correlated_index": "NIFTY"
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # 4. KAYNES (High Precision)
    "KAYNES": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "use_atr_target": True, "atr_multiplier": 2.2,
            "use_atr_sl": True, "atr_sl_multiplier": 1.8,
            "max_ema_dist_atr": 1.5, "adx_min": 25, "max_atr_allowed": 0.05,
            "leverage": 4.0, "max_capital": 20000, "opening_noise_mins": 5,
            "correlated_index": "NIFTY"
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # 5. ABLBL
    "ABLBL": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "use_atr_target": True, "atr_multiplier": 2.0,
            "use_atr_sl": True, "atr_sl_multiplier": 1.5,
            "max_ema_dist_atr": 1.5, "adx_min": 25, "max_atr_allowed": 0.05,
            "leverage": 4.0, "max_capital": 100000, "opening_noise_mins": 5,
            "correlated_index": "NIFTY"
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # 6. SILVERBEES (Parabolic Protection)
    "SILVERBEES": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "use_atr_target": True, "atr_multiplier": 2.0,
            "use_atr_sl": True, "atr_sl_multiplier": 1.5,
            "max_ema_dist_atr": 1.0, "adx_min": 25, "max_atr_allowed": 0.03,
            "leverage": 4.0, "max_capital": 40000, "opening_noise_mins": 3,
            "correlated_index": "NONE"
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # 7. GOLDBEES (Nippon Gold ETF)
    "GOLDBEES": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "use_atr_target": True, "atr_multiplier": 2.0,
            "use_atr_sl": True, "atr_sl_multiplier": 1.5,
            "max_ema_dist_atr": 1.0, "adx_min": 25, "max_atr_allowed": 0.03,
            "leverage": 4.0, "max_capital": 30000, "opening_noise_mins": 5,
            "correlated_index": "NONE"
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # 7. IRFC (The Alpha King)
    "IRFC": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "use_atr_target": True, "atr_multiplier": 2.5,
            "use_atr_sl": True, "atr_sl_multiplier": 2.0,
            "max_ema_dist_atr": 1.2, "adx_min": 30, "max_atr_allowed": 0.07,
            "leverage": 4.0, "max_capital": 30000, "opening_noise_mins": 5,
            "correlated_index": "NIFTY"
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # 8. PAYTM (Volatile Stock - Allow Midday Alignment)
"PAYTM": {
    "strategy_params": {
        "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
        "use_atr_target": True, "atr_multiplier": 3.0,
        "use_atr_sl": True, "atr_sl_multiplier": 2.5,
        "max_ema_dist_atr": 1.5, "adx_min": 25, "max_atr_allowed": 0.05,
        "leverage": 3.0, "max_capital": 30000, 
        "opening_noise_mins": 2,
        # V8 Features: Aggressive Gap & Depth Checks
        "gap_tolerance_pct": 0.005, "use_market_depth": True,
        "partial_exit_atr": 1.2, "partial_qty_pct": 0.5,
        "correlated_index": "BANKNIFTY",
        "allow_alignment_entry": True,  # Enable alignment mode
        "alignment_window_mins": 390    # Allow alignment all day (6.5 hours)
    },
    "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
},


    # 8. SBIN (Blue Chip Smoothing)
    "SBIN": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "use_atr_target": True, "atr_multiplier": 1.8,
            "use_atr_sl": True, "atr_sl_multiplier": 1.5,
            "max_ema_dist_atr": 1.8, "adx_min": 22, "max_atr_allowed": 0.02,
            "leverage": 5.0, "max_capital": 30000, "opening_noise_mins": 5,
            "correlated_index": "BANKNIFTY"
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # 9. OLAELEC (Momentum Disruptor)
    "OLAELEC": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "use_atr_target": True, "atr_multiplier": 2.5,
            "use_atr_sl": True, "atr_sl_multiplier": 2.0,
            "max_ema_dist_atr": 1.5, "adx_min": 30, "max_atr_allowed": 0.08,
            "leverage": 4.0, "max_capital": 100000, "opening_noise_mins": 5,
            "correlated_index": "NIFTY"
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # === UNIVERSAL FALLBACK ===
    "DEFAULT": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "use_atr_target": True, "atr_multiplier": 3.0,
            "use_atr_sl": True, "atr_sl_multiplier": 2.5,
            "max_ema_dist_atr": 1.5, "adx_min": 25, "max_atr_allowed": 0.05,
            "leverage": 3.0, "max_capital": 30000, "opening_noise_mins": 2,
            # V8 Features
            "gap_tolerance_pct": 0.005, "use_market_depth": True,
            "partial_exit_atr": 1.0, "partial_qty_pct": 0.5,
            "correlated_index": "NIFTY"
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    }
}
