"""
Intraday Strategy Diagnostic Tool.
Runs the strategy and logs detailed reasoning for every pair at every bar.
"""
import sys
import os
import pandas as pd
import logging
from datetime import datetime
from typing import Dict

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Algorithms import PairTradingStrategy
from Backtesting import HistoricalDataFetcher
from Backtesting.config import StrategyConfig
from login import get_kite_instance

# Configure specific logger for diagnostics
diag_logger = logging.getLogger("Diagnostic")
diag_logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
diag_logger.addHandler(handler)

def run_diagnostic():
    config = StrategyConfig.INTRADAY_PAIR_TRADING
    kite = get_kite_instance()
    if not kite:
        print("Failed to initialize Kite")
        return
    fetcher = HistoricalDataFetcher(kite)
    
    start_date = "2025-12-08"
    end_date = "2026-01-07"
    interval = "5min"
    
    # 1. Fetch Data
    symbols = list(set([p[0] for p in config['pairs']] + [p[1] for p in config['pairs']]))
        
    all_data = {}
    for sym in symbols:
        df = fetcher.fetch_historical_data(sym, start_date, end_date, interval)
        if df is not None:
            all_data[sym] = df
            
    # 2. Setup Strategy
    strategy = PairTradingStrategy(params=config)
    strategy.market_intel.enabled = False
    
    # Initialize Kalman Filters (same as runner)
    # Get common timeline
    timeline = None
    for sym in all_data:
        if timeline is None:
            timeline = all_data[sym].index
        else:
            timeline = timeline.intersection(all_data[sym].index)
            
    print(f"\n{'Time':<20} | {'Pair':<15} | {'Spread':8} | {'Beta':5} | {'Z':6} | {'RSI':4} | {'Hurst':5} | {'ADF':6} | {'ThreshL':8} | {'ThreshU':8} | {'ATR':5} | {'Status'}")
    print("-" * 140)
    
    for current_time in timeline:
        # Prepare data slice
        data_slice = {}
        for sym in all_data:
            data_slice[sym] = all_data[sym][all_data[sym].index <= current_time]
            
        # Run Strategy
        signals = strategy.generate_signals(data_slice, current_time)
        
        # Log Decisions for each pair
        for asset_a, asset_b in strategy.pairs:
            pair_key = (asset_a, asset_b)
            state = strategy.latest_state.get(pair_key, {})
            
            spread = state.get('spread', 0.0)
            z_score = state.get('z_score', 0.0)
            rsi = state.get('rsi', 50.0)
            hurst = state.get('hurst', 0.5)
            adf = state.get('adf', 0.0)
            beta = state.get('beta', 1.0)
            thresh_upper = state.get('dynamic_thresh_upper', 0.1)
            thresh_lower = state.get('dynamic_thresh_lower', -0.1)
            atr = state.get('atr', 0.0) # Assuming ATR is stored in state
            
            status = "No Signal"
            if any(s.symbol in (asset_a, asset_b) for s in signals):
                sig = next(s for s in signals if s.symbol in (asset_a, asset_b))
                status = f"✅ SIGNAL: {sig.signal_type.name} ({sig.reason})"
            else:
                if thresh_lower <= spread <= thresh_upper:
                    status = f"Inside Band"
                elif hurst > 0.45:
                    status = f"Trending"
                else:
                    status = "Check ADF/Correlation/Time"
            
            # Print first 50 bars and any signals/out-of-bounds thereafter
            if timeline.get_loc(current_time) < 50 or abs(spread) > abs(thresh_upper) or "SIGNAL" in status:
                print(f"{str(current_time):<20} | {asset_a+'-'+asset_b:<15} | {spread:8.4f} | {beta:5.2f} | {z_score:6.2f} | {rsi:4.1f} | {hurst:5.2f} | {adf:6.2f} | {thresh_lower:8.4f} | {thresh_upper:8.4f} | {atr:5.4f} | {status}")

if __name__ == "__main__":
    run_diagnostic()
