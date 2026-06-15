# Paise Trade V2 - 3-Timeframe MTFA Configuration
# Last Updated: June 15, 2026
# Standardized on ATR-based Targets, Stops, and Overextension Guards.

"""
================================================================================
3-TIMEFRAME MTFA CONFIGURATION PARAMETERS CHEAT SHEET
================================================================================

TREND FILTERING & EMA PERIODS:
-----------------------------
* sky_ema_period (int): 
  EMA span on the Higher Time Frame (HTF, "Sky" - typically 1-Hour).
  Determines the macro trend bias (Bullish if price > Sky EMA, Bearish if price < Sky EMA).
* forest_ema_period (int): 
  EMA span on the Medium Time Frame (MTF, "Forest" - typically 30-Min).
  Provides structural confirmation. Entry is blocked unless Sky and Forest biases align.
* tree_ema_period (int): 
  EMA span on the Lower Time Frame (LTF, "Tree" - typically 10-Min).
  Used for crossover signals and short-term trailing stops.

DYNAMIC TARGETS & STOP LOSSES (ATR-BASED):
----------------------------------------
* use_atr_target (bool): 
  If True, profit targets are dynamically calculated using Average True Range (ATR).
  Protects against volatile ranges.
* atr_multiplier (float): 
  Multiplier applied to the 14-period Tree ATR to set the Take Profit target.
  Example: 2.0x ATR profit target.
* use_atr_sl (bool): 
  If True, the Stop Loss is dynamically adjusted based on ATR.
* atr_sl_multiplier (float): 
  Multiplier applied to the 14-period Tree ATR to determine the initial Stop Loss.
  Example: 1.5x ATR stop loss from the entry price.

TRAILING STOP TYPE:
------------------
* trailing_type (str): 
  Option to use "ema" (standard trailing using the Tree or Forest EMA) or 
  "chandelier" (trailing using Chandelier exit logic: peak price - mult * ATR).
* chandelier_multiplier (float): 
  Multiplier applied to ATR for calculating Chandelier trailing stops.

RISK CONTROLS & GATING FILTERS:
------------------------------
* max_ema_dist_atr (float): 
  Overextension threshold (in ATR multiples). Prevents entry if the price is 
  too far away from the Tree EMA to avoid chasing momentum breakouts.
  Example: If distance > 1.5 * ATR, entry is skipped.
* adx_min (float): 
  Minimum ADX trend strength value. Gated so that trading is blocked during 
  flat/sideways markets (ADX < adx_min). Typical value: 25.
* max_atr_allowed (float): 
  Volatility ceiling as a percentage of price. Blocks entries during erratic 
  price moves or corporate events. Example: 0.05 = 5% of price.
* leverage (float): 
  Intraday leverage factor applied to allocation capital.
* max_capital (float): 
  Capital ceiling cap to limit the cash allocation on any single stock.
* opening_noise_mins (int): 
  Number of minutes to ignore signals after the 9:15 AM IST open.
  Filters high morning volatility.

ADVANCED FEATURES:
-----------------
* gap_tolerance_pct (float): 
  Gap threshold from the previous day's close. Gaps exceeding this threshold 
  and matching the trend bias invoke special high-conviction breakout rules.
* use_market_depth (bool): 
  Enable checking bid/ask order book queues before placing live orders to avoid 
  circuit limit freezes or entering illiquid symbols.
* partial_exit_atr (float): 
  Trigger distance in ATR units to sell/cover a portion of the position.
* partial_qty_pct (float): 
  Percentage of open quantity to exit at the partial profit trigger. Example: 0.5 = 50%.
* correlated_index (str): 
  Index filter (e.g. "NIFTY" or "BANKNIFTY"). Trades are blocked if the stock 
  bias goes against the corresponding overall market index bias.
* allow_alignment_entry (bool): 
  Allows entering positions when trend biases align later in the day, rather 
  than requiring an exact fresh EMA crossover.
* alignment_window_mins (int): 
  Time window from market open in which alignment-based entries are allowed.
================================================================================
"""

SYMBOLS = ["INDIGO", "DLF", "ASIANPAINT", "ONGC", "ICICIBANK"]

CONFIG = {
    # -------------------------------------------------------------------------
    # 1. INDIGO (LONG)
    # -------------------------------------------------------------------------
    "INDIGO": {
        "strategy_params": {
            "sky_ema_period": 20,
            "forest_ema_period": 9,
            "tree_ema_period": 9,
            "DIRECTION": "LONG",
            "use_atr_target": False,
            "profit_target": 0.035,        # Target 2
            "partial_exit_pct": 0.02,      # Target 1
            "use_atr_sl": False,
            "stop_loss": 0.015,
            "max_ema_dist_atr": 1.5,
            "adx_min": 25,
            "max_atr_allowed": 0.05,
            "leverage": 3.0,
            "max_capital": 30000,
            "opening_noise_mins": 15,
            "WAIT_FOR_FIRST_15M_CLOSE": True,
            "mean_reversion_pct": 0.02,
            "correlated_index": "NIFTY"
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # -------------------------------------------------------------------------
    # 2. DLF (LONG)
    # -------------------------------------------------------------------------
    "DLF": {
        "strategy_params": {
            "sky_ema_period": 20,
            "forest_ema_period": 9,
            "tree_ema_period": 9,
            "DIRECTION": "LONG",
            "use_atr_target": False,
            "profit_target": 0.025,
            "partial_exit_pct": 0.015,
            "use_atr_sl": False,
            "stop_loss": 0.015,
            "max_ema_dist_atr": 1.5,
            "adx_min": 25,
            "max_atr_allowed": 0.05,
            "leverage": 3.0,
            "max_capital": 30000,
            "opening_noise_mins": 15,
            "WAIT_FOR_FIRST_15M_CLOSE": True,
            "mean_reversion_pct": 0.02,
            "correlated_index": "NIFTY"
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # -------------------------------------------------------------------------
    # 3. ASIANPAINT (LONG)
    # -------------------------------------------------------------------------
    "ASIANPAINT": {
        "strategy_params": {
            "sky_ema_period": 20,
            "forest_ema_period": 9,
            "tree_ema_period": 9,
            "DIRECTION": "LONG",
            "use_atr_target": False,
            "profit_target": 0.03,
            "partial_exit_pct": 0.015,
            "use_atr_sl": False,
            "stop_loss": 0.01,
            "max_ema_dist_atr": 1.5,
            "adx_min": 25,
            "max_atr_allowed": 0.05,
            "leverage": 3.0,
            "max_capital": 30000,
            "opening_noise_mins": 15,
            "WAIT_FOR_FIRST_15M_CLOSE": True,
            "mean_reversion_pct": 0.02,
            "correlated_index": "NIFTY"
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # -------------------------------------------------------------------------
    # 4. ONGC (SHORT)
    # -------------------------------------------------------------------------
    "ONGC": {
        "strategy_params": {
            "sky_ema_period": 20,
            "forest_ema_period": 9,
            "tree_ema_period": 9,
            "DIRECTION": "SHORT",
            "use_atr_target": False,
            "profit_target": 0.025,
            "partial_exit_pct": 0.015,
            "use_atr_sl": False,
            "stop_loss": 0.012,
            "max_ema_dist_atr": 1.5,
            "adx_min": 25,
            "max_atr_allowed": 0.05,
            "leverage": 3.0,
            "max_capital": 30000,
            "opening_noise_mins": 45,      # Increased to 45m to bypass morning short-squeeze
            "WAIT_FOR_FIRST_15M_CLOSE": True,
            "mean_reversion_pct": 0.02,
            "correlated_index": "NIFTY"
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # -------------------------------------------------------------------------
    # 5. ICICIBANK (LONG)
    # -------------------------------------------------------------------------
    "ICICIBANK": {
        "strategy_params": {
            "sky_ema_period": 20,
            "forest_ema_period": 9,
            "tree_ema_period": 9,
            "DIRECTION": "LONG",
            "use_atr_target": False,
            "profit_target": 0.018,
            "partial_exit_pct": 0.01,
            "use_atr_sl": False,
            "stop_loss": 0.008,
            "max_ema_dist_atr": 1.5,
            "adx_min": 25,
            "max_atr_allowed": 0.05,
            "leverage": 3.0,
            "max_capital": 30000,
            "opening_noise_mins": 15,
            "WAIT_FOR_FIRST_15M_CLOSE": True,
            "mean_reversion_pct": 0.02,
            "correlated_index": "BANKNIFTY"
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    },

    # -------------------------------------------------------------------------
    # 6. DEFAULT / UNIVERSAL FALLBACK
    # -------------------------------------------------------------------------
    "DEFAULT": {
        "strategy_params": {
            "sky_ema_period": 20,
            "forest_ema_period": 9,
            "tree_ema_period": 9,
            "use_atr_target": True,
            "atr_multiplier": 3.0,
            "use_atr_sl": True,
            "atr_sl_multiplier": 2.5,
            "max_ema_dist_atr": 1.5,
            "adx_min": 25,
            "max_atr_allowed": 0.05,
            
            # Default V8 options
            "gap_tolerance_pct": 0.005,
            "use_market_depth": True,
            "partial_exit_atr": 1.0,
            "partial_qty_pct": 0.5,
            
            "leverage": 3.0,
            "max_capital": 30000,
            "opening_noise_mins": 2,
            "correlated_index": "NIFTY"
        },
        "lookbacks": {"10m": 110, "30m": 60, "1h": 50}
    }
}
