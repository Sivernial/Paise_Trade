import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Backtesting.data_fetcher import HistoricalDataFetcher
from login import get_kite_instance

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

SYMBOL = "ITC"

def analyze_jan20():
    kite = get_kite_instance()
    fetcher = HistoricalDataFetcher(kite)
    
    test_date = datetime(2026, 1, 20)
    
    df_10m = fetcher.fetch_historical_data(SYMBOL, test_date, test_date + timedelta(days=1), interval="10minute")
    df_1h = fetcher.fetch_historical_data(SYMBOL, test_date - timedelta(days=30), test_date + timedelta(days=1), interval="60minute")
    
    if df_10m.index.tz: df_10m.index = df_10m.index.tz_localize(None)
    if df_1h.index.tz: df_1h.index = df_1h.index.tz_localize(None)
    
    # Calculate indicators
    df_1h['ema20'] = df_1h['close'].ewm(span=20, adjust=False).mean()
    df_10m['ema9'] = df_10m['close'].ewm(span=9, adjust=False).mean()
    
    print(f"\n{'='*60}")
    print(f"ITC Analysis for January 20, 2026")
    print(f"{'='*60}\n")
    
    # Show 1H trend at market open
    jan20_1h = df_1h[df_1h.index.date == test_date.date()]
    if not jan20_1h.empty:
        print("1H FOREST (Hourly Trend):")
        print(jan20_1h[['close', 'ema20']].to_string())
        last_1h = jan20_1h.iloc[-1]
        bias = "BULLISH" if last_1h['close'] > last_1h['ema20'] else "BEARISH"
        print(f"\nForest Bias: {bias} (Price: {last_1h['close']:.2f}, EMA20: {last_1h['ema20']:.2f})")
    
    print(f"\n{'-'*60}\n")
    
    # Show 10m action
    print("10M TREES (Intraday Execution):")
    print(df_10m[['close', 'ema9']].to_string())
    
    print(f"\n{'-'*60}\n")
    
    # Check alignment
    print("MTFA ALIGNMENT CHECK:")
    for idx, row in df_10m.iterrows():
        price = row['close']
        ema9 = row['ema9']
        
        # Get 1H bias at this time
        forest_data = df_1h[df_1h.index <= idx - timedelta(hours=1)]
        if len(forest_data) >= 20:
            forest_data_copy = forest_data.copy()
            forest_data_copy['ema'] = forest_data_copy['close'].ewm(span=20, adjust=False).mean()
            f_price = forest_data_copy['close'].iloc[-1]
            f_ema = forest_data_copy['ema'].iloc[-1]
            f_bias = "BULL" if f_price > f_ema else "BEAR"
            
            aligned = (f_bias == "BULL" and price > ema9) or (f_bias == "BEAR" and price < ema9)
            
            print(f"{idx.strftime('%H:%M')} | Price: {price:.2f} | EMA9: {ema9:.2f} | Forest: {f_bias} | {'✓ ALIGNED' if aligned else '✗ NOT ALIGNED'}")

if __name__ == "__main__":
    analyze_jan20()
