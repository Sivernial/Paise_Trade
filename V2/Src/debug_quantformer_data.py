import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from Common.quant_utils import calculate_pca_residuals
from Backtesting import HistoricalDataFetcher
from login import get_kite_instance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASKET = ['SBIN', 'PNB', 'BANKBARODA', 'CANBK', 'IDFCFIRSTB']

def debug_data():
    kite = get_kite_instance()
    fetcher = HistoricalDataFetcher(kite)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)
    
    raw_data, resampled_data = fetcher.fetch_and_resample(BASKET, start_date, end_date, "5min", "5min")
    
    common_idx = None
    for s in BASKET:
        if s in resampled_data:
            if common_idx is None:
                common_idx = resampled_data[s].index
            else:
                common_idx = common_idx.intersection(resampled_data[s].index)
                
    prices = pd.DataFrame({s: resampled_data[s].loc[common_idx]['close'] for s in BASKET})
    
    log_rets = np.log(prices / prices.shift(1)).dropna()
    residuals = calculate_pca_residuals(log_rets, n_components=1)
    cum_residuals = residuals.cumsum()
    
    sym = 'SBIN'
    target = cum_residuals[sym].shift(-3) - cum_residuals[sym]
    
    logger.info(f"--- Data Stats for {sym} ---")
    logger.info(f"Residual Mean: {residuals[sym].mean():.6f}")
    logger.info(f"Residual Std: {residuals[sym].std():.6f}")
    logger.info(f"Target (3-bar change) Mean: {target.mean():.6f}")
    logger.info(f"Target (3-bar change) Std: {target.std():.6f}")
    logger.info(f"Target Min: {target.min():.6f}")
    
    # Inference Check
    from AI.quantformer import QuantformerPredictor
    
    predictor = QuantformerPredictor(input_dim=5, seq_len=30)
    predictor.load()
    
    # Create sample feature df
    df = pd.DataFrame()
    df['res'] = cum_residuals[sym]
    df['res_lag1'] = df['res'].shift(1)
    df['vol'] = log_rets[sym].rolling(10).std()
    df['volume'] = resampled_data[sym]['volume']
    df['volume'] = df['volume'] / df['volume'].rolling(50).mean()
    df['res_ma'] = df['res'].rolling(20).mean()
    
    df = df.dropna()
    df = (df - df.mean()) / df.std()
    
    logger.info("--- Model Predictions (Last 5) ---")
    # Take random 5 samples from middle
    start_idx = len(df) // 2
    for i in range(start_idx, start_idx+5):
        sample = df.iloc[i:i+30]
        if len(sample) == 30:
            pred = predictor.predict(sample)
            logger.info(f"Prediction: {pred:.6f}")

if __name__ == "__main__":
    debug_data()
