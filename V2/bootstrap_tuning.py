import sys
import os
import pandas as pd
import numpy as np
import json
import logging
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'Src')))

from Backtesting.data_fetcher import HistoricalDataFetcher
from Common.quant_utils import calculate_pca_residuals, calculate_hurst, calculate_adx
from login import get_kite_instance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASKETS = {
    'Banking': ['SBIN', 'PNB', 'BANKBARODA', 'CANBK', 'IDFCFIRSTB'],
    'IT': ['INFY', 'TCS', 'HCLTECH', 'TECHM', 'WIPRO'],
    'Auto': ['MARUTI', 'M&M', 'TMPV', 'BAJAJ-AUTO', 'EICHERMOT'],
    'Pharma': ['SUNPHARMA', 'CIPLA', 'DRREDDY', 'DIVISLAB'],
    'Energy': ['RELIANCE', 'NTPC', 'POWERGRID', 'ONGC', 'COALINDIA']
}

def bootstrap_config():
    kite = get_kite_instance()
    fetcher = HistoricalDataFetcher(kite)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30) # 30 Days lookback for robust stats
    
    all_symbols = [s for basket in BASKETS.values() for s in basket]
    logger.info(f"Fetching 30 days of data for {len(all_symbols)} symbols...")
    
    # Fetch Data
    raw_data, data = fetcher.fetch_and_resample(all_symbols, start_date, end_date, "5min", "5min")
    
    optimized_config = {}
    
    for basket_name, symbols in BASKETS.items():
        logger.info(f"Processing {basket_name}...")
        
        # Prepare Basket Data
        basket_df = pd.DataFrame()
        for sym in symbols:
            if sym in data:
                # Deduplicate
                s = data[sym]['close']
                s = s[~s.index.duplicated(keep='last')]
                basket_df[sym] = s
        
        basket_df.dropna(inplace=True)
        
        if basket_df.empty: continue
        
        # PCA Residuals (Lookback 180 matching strategy)
        # We calculate rolling residuals effectively
        log_returns = np.log(basket_df / basket_df.shift(1)).dropna()
        
        # We need a rolling window to mimic the strategy exactly, but for bulk stats 
        # extracting residuals on the whole period is a decent approximation for "Characteristic Volatility"
        # However, to be precise, let's use the static PCA on the whole window to find the "Regime Distribution"
        
        residuals = calculate_pca_residuals(log_returns, n_components=1)
        # Normalize residuals to Z-scores (Rolling 180)
        
        for symbol in symbols:
            if symbol not in residuals.columns: continue
            
            res_series = residuals[symbol]
            
            # Calculate Rolling Z-Score (Window 180)
            roll_mean = res_series.rolling(window=180).mean()
            roll_std = res_series.rolling(window=180).std()
            z_scores = (res_series - roll_mean) / roll_std
            
            # Filter for valid data
            df_sym = pd.DataFrame({'z': z_scores}).dropna()
            
            # We can't easily calculate rolling Hurst efficiently for every candle in this script without being slow
            # So we will use a simplified robust heuristic:
            # 95th Percentile of ALL Z-scores. 
            # This generally captures the "Edge" of the distribution.
            
            if not df_sym.empty:
                # Absolute Z-scores
                abs_z = df_sym['z'].abs()
                
                # Percentile Optimization
                # We use 95th percentile as the "Reversion Boundary"
                suggested_z = round(abs_z.quantile(0.95), 2)
                
                # Clamp to safe limits [1.8, 3.2]
                # slightly looser max than TuningEngine to allow for high-vol stocks
                suggested_z = max(1.8, min(3.2, suggested_z))
                
                optimized_config[symbol] = suggested_z
                logger.info(f"  {symbol}: {suggested_z}")
    
    # Save Config
    final_output = {
        "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "symbol_thresholds": optimized_config
    }
    
    with open("strategy_config.json", "w") as f:
        json.dump(final_output, f, indent=4)
    
    logger.info("Bootstrap Complete! strategy_config.json updated.")

if __name__ == "__main__":
    bootstrap_config()
