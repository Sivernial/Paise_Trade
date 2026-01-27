
# 3-Timeframe MTFA Configuration
# UPDATED: Jan 26, 2026 - OPTIMIZED for High Volatility V3 List

CONFIG = {
    # === THE V3 VOLATILITY KINGS (Optimized for 4%+ ATR) ===
    
    # 1. ADANI GREEN
    "ADANIGREEN": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "use_atr_target": True, "atr_multiplier": 2.5,
            "profit_target": 0.035, "stop_loss": 0.02, "leverage": 4.0, 
            "max_capital": 100000, "opening_noise_mins": 5
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # 2. ETERNAL (ZOMATO)
    "ETERNAL": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "use_atr_target": True, "atr_multiplier": 2.0,
            "profit_target": 0.03, "stop_loss": 0.015, "leverage": 4.0, 
            "max_capital": 20000, "opening_noise_mins": 5
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # 3. ADANI ENSOL
    "ADANIENSOL": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "use_atr_target": True, "atr_multiplier": 2.0,
            "profit_target": 0.025, "stop_loss": 0.02, "leverage": 4.0, 
            "max_capital": 100000, "opening_noise_mins": 5
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # 4. KAYNES
    "KAYNES": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "use_atr_target": True, "atr_multiplier": 2.0,
            "profit_target": 0.03, "stop_loss": 0.018, "leverage": 4.0, 
            "max_capital": 20000, "opening_noise_mins": 5
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # 5. ABLBL
    "ABLBL": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "use_atr_target": True, "atr_multiplier": 2.0,
            "profit_target": 0.025, "stop_loss": 0.015, "leverage": 4.0, 
            "max_capital": 100000, "opening_noise_mins": 5
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # 6. DR REDDY
    "DRREDDY": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "use_atr_target": True, "atr_multiplier": 1.5,
            "profit_target": 0.015, "stop_loss": 0.007, "leverage": 4.0, 
            "max_capital": 100000, "opening_noise_mins": 5
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # 7. SILVERBEES
    "SILVERBEES": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "use_atr_target": True, "atr_multiplier": 2.0,
            "profit_target": 0.015, "stop_loss": 0.005, "leverage": 4.0, 
            "max_capital": 100000, "opening_noise_mins": 5
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # 8. RVNL (Alpha V3 King: 6.2% ATR)
    "RVNL": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "profit_target": 0.05, "stop_loss": 0.025, "leverage": 4.0, 
            "max_capital": 50000, "opening_noise_mins": 5
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # 9. IRFC (Alpha V3 King: 5.8% ATR)
    "IRFC": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "profit_target": 0.04, "stop_loss": 0.02, "leverage": 4.0, 
            "max_capital": 50000, "opening_noise_mins": 5
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # 10. POLYCAB (Alpha V3 Bear: 3.3% ATR)
    "POLYCAB": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "profit_target": 0.03, "stop_loss": 0.015, "leverage": 4.0, 
            "max_capital": 100000, "opening_noise_mins": 5
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # === UNIVERSAL FALLBACK ===
    "DEFAULT": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "use_atr_target": True, "atr_multiplier": 2.0,
            "profit_target": 0.015, "stop_loss": 0.005, "leverage": 5.0, 
            "max_capital": 100000, "opening_noise_mins": 5
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    }
}
