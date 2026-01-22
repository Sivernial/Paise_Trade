import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import logging

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from Backtesting.data_fetcher import HistoricalDataFetcher
from Src.login import get_kite_instance
from Algorithms.silver_sentinel_strategy import SilverSentinelStrategy
from Common.quant_utils import calculate_vwap

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Diagnostic")

def run_diagnostic():
    kite = get_kite_instance()
    fetcher = HistoricalDataFetcher(kite)
    
    target_date = datetime(2026, 1, 22)
    
    # Fetch data
    df_10m = fetcher.fetch_historical_data("SILVERBEES", target_date - timedelta(days=10), target_date + timedelta(days=1), interval="10minute")
    df_1h = fetcher.fetch_historical_data("SILVERBEES", target_date - timedelta(days=40), target_date + timedelta(days=1), interval="60minute")
    
    if df_10m.index.tz: df_10m.index = df_10m.index.tz_localize(None)
    if df_1h.index.tz: df_1h.index = df_1h.index.tz_localize(None)
    
    # Execution day (9:15 AM to 3:30 PM)
    df_day = df_10m[(df_10m.index >= target_date.replace(hour=9, minute=15)) & 
                    (df_10m.index <= target_date.replace(hour=15, minute=30))]
    
    print("\n" + "="*95)
    print(f"DIAGNOSTIC: SILVERBEES Jan 22 Full Day")
    print("="*95)
    print(f"{'Time':<20} | {'Price':<8} | {'ForestEMA':<10} | {'TreeEMA':<8} | {'VWAP':<8} | {'Bias':<8}")
    print("-" * 95)
    
    for current_time in df_day.index:
        price = df_10m.loc[current_time, 'close']
        
        # Forest (1H)
        full_df_1h = df_1h[df_1h.index < current_time]
        ema_forest = full_df_1h['close'].ewm(span=20, adjust=False).mean().iloc[-1]
        bias = "BULL" if full_df_1h['close'].iloc[-1] > ema_forest else "BEAR"
        
        # Trees (10m)
        full_df_10m = df_10m[df_10m.index <= current_time]
        ema_tree = full_df_10m['close'].ewm(span=9, adjust=False).mean().iloc[-1]
        vwap_val = calculate_vwap(full_df_10m).iloc[-1]
        
        print(f"{current_time.strftime('%H:%M:%S'):<20} | {price:<8.2f} | {ema_forest:<10.2f} | {ema_tree:<8.2f} | {vwap_val:<8.2f} | {bias:<8}")

if __name__ == "__main__":
    run_diagnostic()
