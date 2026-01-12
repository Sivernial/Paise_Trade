import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from AI.multi_factor_predictor import MultiFactorPredictor
from Common.quant_utils import calculate_pca_residuals
from Backtesting import HistoricalDataFetcher
from login import get_kite_instance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sector Baskets
BASKETS = {
    'Banking': ['SBIN', 'PNB', 'BANKBARODA', 'CANBK', 'IDFCFIRSTB'],
    'IT': ['INFY', 'TCS', 'HCLTECH', 'TECHM', 'WIPRO'],
    'Auto': ['MARUTI', 'M&M', 'TMPV', 'BAJAJ-AUTO', 'EICHERMOT'],
    'Pharma': ['SUNPHARMA', 'CIPLA', 'DRREDDY', 'DIVISLAB']
}

def train_v3():
    kite = get_kite_instance()
    fetcher = HistoricalDataFetcher(kite)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60) # 60 days of data
    
    predictor = MultiFactorPredictor()
    all_features = []
    all_targets = []
    
    for sector, symbols in BASKETS.items():
        logger.info(f"--- Processing Sector: {sector} ---")
        
        logger.info(f"Fetching data for basket: {symbols}")
        raw_data, resampled_data = fetcher.fetch_and_resample(symbols, start_date, end_date, "5min", "5min")
        
        if not resampled_data or len(resampled_data) < len(symbols):
            logger.warning(f"Insufficient data for {sector}, skipping.")
            continue

        # 1. Prepare Price Matrix
        # Ensure alignment
        common_index = None
        for sym in symbols:
            if sym in resampled_data:
                if common_index is None:
                    common_index = resampled_data[sym].index
                else:
                    common_index = common_index.intersection(resampled_data[sym].index)
        
        if common_index is None or len(common_index) == 0:
             continue
             
        prices = pd.DataFrame({sym: resampled_data[sym].loc[common_index]['close'] for sym in symbols})
        volume = pd.DataFrame({sym: resampled_data[sym].loc[common_index]['volume'] for sym in symbols})
        
        # 2. Log Returns PCA
        log_returns = np.log(prices / prices.shift(1)).dropna()
        if log_returns.empty: continue
        
        residuals = calculate_pca_residuals(log_returns, n_components=1)
        cum_residuals = residuals.cumsum()
        
        # 3. Label: Predict residual return over next 3 bars (15 mins)
        horizon = 3
        
        for symbol in symbols:
            feat_df = predictor.extract_features(cum_residuals[symbol], volume[symbol])
            
            # Target: Difference in cumulative residual over horizon
            target = cum_residuals[symbol].shift(-horizon) - cum_residuals[symbol]
            target = target.loc[feat_df.index].dropna()
            
            feat_df = feat_df.loc[target.index]
            
            all_features.append(feat_df)
            all_targets.append(target)
            
    if not all_features:
        logger.error("No training data generated.")
        return
        
    X = pd.concat(all_features)
    y = pd.concat(all_targets)
    
    # 4. Train
    logger.info(f"Training on {len(X)} samples across {len(BASKETS)} sectors.")
    predictor.train(X, y)
    logger.info("V3 Multi-Sector Training Complete.")

if __name__ == "__main__":
    train_v3()
