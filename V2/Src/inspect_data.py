import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, timedelta
import pandas as pd
from Backtesting import HistoricalDataFetcher
from Backtesting.config import MarketDataConfig
from login import get_kite_instance

def inspect_data():
    kite = get_kite_instance()
    if not kite:
        print("Login failed")
        return
        
    fetcher = HistoricalDataFetcher(kite)
    
    # Symbols to inspect
    symbols = ["TMPV", "M&M", "ACC", "AMBUJACEM", "TCS", "INFY"]
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    print(f"Fetching data from {start_date.date()} to {end_date.date()}")
    
    for symbol in symbols:
        try:
            print(f"\n--- {symbol} ---")
            df = fetcher.fetch_historical_data(symbol, start_date, end_date, interval="5minute")
            
            if df.empty:
                print("No data.")
                continue
                
            print(f"Rows: {len(df)}")
            print(f"Min Close: {df['close'].min()}")
            print(f"Max Close: {df['close'].max()}")
            print(f"Mean Close: {df['close'].mean()}")
            
            # Check for sudden drops/spikes (> 20% in one bar)
            df['pct_change'] = df['close'].pct_change()
            anomalies = df[abs(df['pct_change']) > 0.20]
            
            if not anomalies.empty:
                print("⚠️ ANOMALIES FOUND (>20% move):")
                print(anomalies[['close', 'pct_change']])
            else:
                print("No major single-bar anomalies.")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    inspect_data()
