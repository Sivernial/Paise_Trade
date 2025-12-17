
import sys
import os
import pandas as pd
import itertools
from datetime import datetime, timedelta

# Add parent directory (V2) to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Src.login import get_kite_instance
from Backtesting.data_fetcher import HistoricalDataFetcher
from Common.quant_utils import calculate_hedge_ratio, calculate_adf_statistic, calculate_half_life

# Define Sector Baskets
SECTORS = {
    'AUTO': ['TATAMOTORS', 'MARUTI', 'M&M', 'BAJAJ-AUTO', 'HEROMOTOCO', 'EICHERMOT', 'ASHOKLEY', 'TVSMOTOR'],
    'IT': ['TCS', 'INFY', 'HCLTECH', 'WIPRO', 'TECHM', 'LTIM', 'OFSS'],
    'BANKS': ['HDFCBANK', 'ICICIBANK', 'SBIN', 'KOTAKBANK', 'AXISBANK', 'INDUSINDBK'],
    'METALS': ['TATASTEEL', 'HINDALCO', 'JSWSTEEL', 'VEDL', 'JINDALSTEL', 'SAIL'],
    'CEMENT': ['ULTRACEMCO', 'GRASIM', 'ACC', 'AMBUJACEM'],
    'PHARMA': ['SUNPHARMA', 'DRREDDY', 'CIPLA', 'DIVISLAB'],
}

def scan_pairs(days=90):
    kite = get_kite_instance()
    fetcher = HistoricalDataFetcher(kite)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    print(f"Fetching data from {start_date.date()} to {end_date.date()}...")
    
    # Flatten all symbols
    all_symbols = []
    for sector, symbols in SECTORS.items():
        all_symbols.extend(symbols)
    
    # Remove duplicates
    all_symbols = list(set(all_symbols))
    
    # Fetch Data
    data_map = {}
    for symbol in all_symbols:
        try:
            print(f"Fetching {symbol}...", end='\r')
            df = fetcher.fetch_historical_data(symbol, start_date, end_date, interval="15min")
            if df is not None and not df.empty:
                data_map[symbol] = df['close']
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            
    print(f"\nFetched {len(data_map)} valid symbols.")
    
    results = []
    
    # Iterate Combinations
    pairs = list(itertools.combinations(data_map.keys(), 2))
    print(f"Scanning {len(pairs)} pairs...")
    
    for asset_a, asset_b in pairs:
        try:
            series_a = data_map[asset_a]
            series_b = data_map[asset_b]
            
            # Align Data
            common_idx = series_a.index.intersection(series_b.index)
            if len(common_idx) < 100:
                continue
                
            s_a = series_a.loc[common_idx]
            s_b = series_b.loc[common_idx]
            
            # Calculate Hedge Ratio
            beta = calculate_hedge_ratio(s_a, s_b)
            
            # Filter unstable betas
            if not (0.2 <= abs(beta) <= 4.0):
                continue
                
            # Calculate Spread
            spread = s_a - beta * s_b
            
            # Cointegration (ADF t-stat)
            # t-stat < -2.57 implies ~10% significance, < -3.43 implies ~1%
            adf_stat = calculate_adf_statistic(spread)
            
            # Half Life
            half_life = calculate_half_life(spread)
            
            # Correlation
            corr = s_a.corr(s_b)
            
            results.append({
                'Pair': f"{asset_a}-{asset_b}",
                'Asset A': asset_a,
                'Asset B': asset_b,
                'Beta': beta,
                'ADF Stat': adf_stat,
                'Half Life': half_life,
                'Correlation': corr
            })
            
        except Exception as e:
            continue

    # Convert to DataFrame
    res_df = pd.DataFrame(results)
    
    if res_df.empty:
        print("No valid pairs found.")
        return

    # Filter High Quality Pairs (ADF < -2.5 and Half Life > 0)
    # The more negative the ADF, the better.
    res_df = res_df[res_df['Half Life'] > 0] 
    res_df = res_df.sort_values(by='ADF Stat', ascending=True)
    
    print("\n" + "="*80)
    print("TOP 20 COINTEGRATED PAIRS")
    print("="*80)
    print(res_df.head(20).to_string(index=False))
    
    # Save to CSV
    output_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pair_scan_results.csv")
    res_df.to_csv(output_path, index=False)
    print(f"\nResults saved to {output_path}")
    
    return res_df

if __name__ == "__main__":
    scan_pairs()
