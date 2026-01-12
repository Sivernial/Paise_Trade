import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from Backtesting import HistoricalDataFetcher
from login import get_kite_instance
from Common.microstructure import calculate_volatility_regime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
BASKETS = {
    'Banking': ['SBIN', 'PNB'],
    'IT': ['TCS', 'INFY'],
    'Auto': ['MARUTI', 'M&M'],
    'Pharma': ['SUNPHARMA', 'CIPLA']
}

def validate_ofi():
    kite = get_kite_instance()
    fetcher = HistoricalDataFetcher(kite)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60) # 2 months data
    
    all_symbols = [s for sublist in BASKETS.values() for s in sublist]
    logger.info(f"Fetching data for {len(all_symbols)} symbols...")
    
    raw, resampled = fetcher.fetch_and_resample(all_symbols, start_date, end_date, "5min", "5min")
    
    results = []
    
    for sym, df in resampled.items():
        if len(df) < 500: continue
        
        # Calculate Volatility Ratio (Microstructure feature for RL)
        df['vol_ratio'] = calculate_volatility_regime(df)
        
        # Calculate Future Returns (Absolute Magnitude)
        # We test if VolRatio(t) predicts |Return(t+1)| (Volatility Clustering)
        df['ret_1bar'] = np.abs(np.log(df['close'].shift(-1) / df['close']))
        df['ret_5bar'] = np.abs(np.log(df['close'].shift(-5) / df['close']))
        
        # Calculate Correlation
        corr_pred_1 = df['vol_ratio'].corr(df['ret_1bar'])
        corr_pred_5 = df['vol_ratio'].corr(df['ret_5bar'])
        
        results.append({
            'Symbol': sym,
            'IC_Pred_1Bar_Abs': corr_pred_1,
            'IC_Pred_5Bar_Abs': corr_pred_5
        })
        
    res_df = pd.DataFrame(results)
    print("\n=== Volatility Validation Results (Correlation w/ Abs Return) ===")
    print(res_df.round(4))
    print("\nMean Predictive IC (1-Bar Abs):", res_df['IC_Pred_1Bar_Abs'].mean())
    
    if res_df['IC_Pred_1Bar_Abs'].mean() > 0.05: # Threshold for significance
        logger.info("VALIDATION SUCCESSFUL: Volatility predicts Magnitude.")
    else:
        logger.warning("VALIDATION WEAK: OFI correlation is low or negative.")

if __name__ == "__main__":
    validate_ofi()
