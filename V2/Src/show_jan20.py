import sys
import os
import pandas as pd
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Backtesting.data_fetcher import HistoricalDataFetcher
from login import get_kite_instance

SYMBOL = "ITC"

def show_jan20_data():
    kite = get_kite_instance()
    fetcher = HistoricalDataFetcher(kite)
    
    test_date = datetime(2026, 1, 20)
    
    # Fetch just Jan 20
    df_10m = fetcher.fetch_historical_data(SYMBOL, test_date, test_date + timedelta(days=1), interval="10minute")
    df_1h = fetcher.fetch_historical_data(SYMBOL, test_date, test_date + timedelta(days=1), interval="60minute")
    
    if df_10m.index.tz: df_10m.index = df_10m.index.tz_localize(None)
    if df_1h.index.tz: df_1h.index = df_1h.index.tz_localize(None)
    
    print(f"\n{'='*60}")
    print(f"ITC Data for January 20, 2026 ONLY")
    print(f"{'='*60}\n")
    
    print(f"10-Minute Bars on Jan 20: {len(df_10m)}")
    print(f"1-Hour Bars on Jan 20: {len(df_1h)}")
    
    print(f"\n1H Bars (should be ~6-7):")
    print(df_1h[['open', 'high', 'low', 'close', 'volume']])
    
    print(f"\n10M Bars (should be ~38):")
    print(df_10m[['open', 'high', 'low', 'close', 'volume']])

if __name__ == "__main__":
    show_jan20_data()
