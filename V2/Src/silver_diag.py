import sys
import os
import pandas as pd
from datetime import datetime, timedelta

# Add project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Backtesting.data_fetcher import HistoricalDataFetcher
from login import get_kite_instance

kite = get_kite_instance()
fetcher = HistoricalDataFetcher(kite)
df = fetcher.fetch_historical_data("SILVERBEES", datetime.now()-timedelta(days=10), datetime.now(), interval="10minute")

if not df.empty:
    df['range'] = (df['high'] - df['low']) / df['close'] * 100
    avg_range = df['range'].mean()
    print(f"Average 10m Bar Range: {avg_range:.4f}%")
    
    # Check Daily Range
    df['date'] = df.index.date
    daily = df.groupby('date').apply(lambda x: (x['high'].max() - x['low'].min()) / x['close'].iloc[0] * 100)
    print(f"Average Daily Range: {daily.mean():.4f}%")
