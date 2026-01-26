
# 3-Timeframe MTFA Configuration
# UPDATED: Jan 26, 2026 based on V3 Screener (High RVol + 1W Momentum)

CONFIG = {
    # === UNIVERSAL FALLBACK (For any new/untested stock) ===
    "DEFAULT": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "profit_target": 0.015, "stop_loss": 0.005, "leverage": 4.0, 
            "max_capital": 100000, "opening_noise_mins": 5
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # === NEW ADDITIONS (Testing Volatility Params) ===
    "ADANIENSOL": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "profit_target": 0.025, "stop_loss": 0.012, "leverage": 4.0, 
            "max_capital": 100000, "opening_noise_mins": 5
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },
    "KAYNES": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "profit_target": 0.025, "stop_loss": 0.012, "leverage": 4.0, 
            "max_capital": 100000, "opening_noise_mins": 5
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },
    "ABLBL": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "profit_target": 0.025, "stop_loss": 0.012, "leverage": 4.0, 
            "max_capital": 100000, "opening_noise_mins": 5
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # === THE V3 VOLATILITY KINGS (Active High-Volume Trends) ===
    "ADANIGREEN": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "profit_target": 0.03, "stop_loss": 0.015, "leverage": 4.0, 
            "max_capital": 100000, "opening_noise_mins": 5
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },
    "ETERNAL": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "profit_target": 0.025, "stop_loss": 0.01, "leverage": 4.0, 
            "max_capital": 100000, "opening_noise_mins": 5
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },
    "ADANIENT": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "profit_target": 0.025, "stop_loss": 0.01, "leverage": 4.0, 
            "max_capital": 100000, "opening_noise_mins": 5
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },
    "DRREDDY": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "profit_target": 0.015, "stop_loss": 0.005, "leverage": 4.0, 
            "max_capital": 100000, "opening_noise_mins": 5
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },
    "ADANIPORTS": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "profit_target": 0.02, "stop_loss": 0.01, "leverage": 4.0, 
            "max_capital": 100000, "opening_noise_mins": 5
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },
    "SILVERBEES": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "profit_target": 0.015, "stop_loss": 0.005, "leverage": 4.0, 
            "max_capital": 100000, "opening_noise_mins": 5
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },
    "INDIGO": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "profit_target": 0.02, "stop_loss": 0.01, "leverage": 4.0, 
            "max_capital": 100000, "opening_noise_mins": 5
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # === LEGACY ===
    "ASHOKLEY": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "profit_target": 0.02, "stop_loss": 0.01, "leverage": 4.0, "max_capital": 100000
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },
    "ITC": {
        "strategy_params": {
            "sky_ema_period": 20, "forest_ema_period": 9, "tree_ema_period": 9,
            "profit_target": 0.008, "stop_loss": 0.004, "leverage": 4.0, "max_capital": 100000
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    }
}
