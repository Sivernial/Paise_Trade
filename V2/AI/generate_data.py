import sys
import os

# Add V2 root and Src to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    
src_dir = os.path.join(parent_dir, 'Src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

import pandas as pd
import numpy as np
from datetime import timedelta, datetime
from Algorithms.pair_trading_strategy import PairTradingStrategy
from Backtesting.data_fetcher import HistoricalDataFetcher
from Backtesting.config import MarketDataConfig
from AI.feature_engineer import FeatureEngineer
from login import get_kite_instance
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_training_data():
    kite = get_kite_instance()
    fetcher = HistoricalDataFetcher(kite)
    
    # Configuration
    # Expanded Universe (Nifty 50 Sector Pairs)
    pairs = [
        ('ACC', 'AMBUJACEM'),      # Cement
        ('ULTRACEMCO', 'GRASIM'),
        ('HDFCBANK', 'ICICIBANK'), # Banks
        ('AXISBANK', 'SBIN'),
        ('KOTAKBANK', 'HDFCBANK'),
        ('INFY', 'TCS'),           # IT
        ('HCLTECH', 'WIPRO'),
        ('TECHM', 'TCS'),
        ('TMPV', 'M&M'),     # Auto
        ('HEROMOTOCO', 'BAJAJ-AUTO'),
        ('MARUTI', 'TMPV'),
        ('TATASTEEL', 'JINDALSTEL'), # Metals
        ('HINDALCO', 'VEDL'),
        ('SUNPHARMA', 'DRREDDY'),  # Pharma
        ('CIPLA', 'SUNPHARMA')
    ]
    lookback_days = 60 # More history for training
    future_window = 12 # Look forward 12 bars (e.g. 3 hours on 15m) for labeling
    profit_threshold = 0.003 # 0.2% Target for binary label
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)
    
    dataset = []
    
    for asset_a, asset_b in pairs:
        logger.info(f"Processing Pair: {asset_a}-{asset_b}")
        
        try:
            # 1. Fetch Data
            result = fetcher.fetch_and_resample(
                [asset_a, asset_b], 
                start_date, end_date, 
                MarketDataConfig.FETCH_INTERVAL, 
                MarketDataConfig.SIGNAL_INTERVAL
            )
            
            if not result or len(result) < 2:
                logger.warning(f"Failed to fetch data for {asset_a}-{asset_b}")
                continue
                
            data = result[1] # Get resampled data
            
            if asset_a not in data or asset_b not in data:
                 logger.warning(f"Missing data for {asset_a} or {asset_b}")
                 continue
            
            if len(data[asset_a]) != len(data[asset_b]):
                min_len = min(len(data[asset_a]), len(data[asset_b]))
                data[asset_a] = data[asset_a].iloc[-min_len:]
                data[asset_b] = data[asset_b].iloc[-min_len:]
                
            df_a = data[asset_a]
            df_b = data[asset_b]

            if df_a.empty or df_b.empty:
                logger.warning(f"Empty data for {asset_a}-{asset_b}")
                continue

        except Exception as e:
            logger.error(f"Error fetching/processing {asset_a}-{asset_b}: {e}")
            continue
        
        # 2. Initialize Strategy (to access logic)
        strategy = PairTradingStrategy({'pairs': [(asset_a, asset_b)]})
        
        # 3. Simulate Loop
        # Needs minimum history for indicators
        warmup = 50 
        
        for i in range(warmup, len(df_a) - future_window):
            # Window for calculation
            window_a = df_a.iloc[:i+1]
            window_b = df_b.iloc[:i+1]
            
            # --- STRATEGY LOGIC COPY START ---
            # Ideally this should be decoupled, but accessing internal state is easier this way
            # Update Kalman
            current_date = window_a.index[-1]
            
            # Use Strategy helper (we need to be careful with stateful Kalman)
            # Actually, using the strategy methods is stateful. 
            # We can re-instantiate or just update manually.
            # Let's use the KF directly here to be consistent with loop
            
            price_a = window_a.iloc[-1]['close']
            price_b = window_b.iloc[-1]['close']
            
            # Update KF
            kf = strategy.kf_registry[(asset_a, asset_b)]
            beta = kf.update(price_a, price_b)
            
            # Z-Score
            spread_series = window_a['close'] - beta * window_b['close']
            mean = spread_series.rolling(strategy.lookback).mean().iloc[-1]
            std = spread_series.rolling(strategy.lookback).std().iloc[-1]
            if std == 0: continue
            
            z_score = (spread_series.iloc[-1] - mean) / std
            
            # Generate Features
            current_adf = -3.0 # Mocking/Optimizing speed vs accuracy. 
            # Or call calculate_adf_statistic(spread_series) if fast enough
            
            features = FeatureEngineer.extract_features(
                window_a, window_b, spread_series, z_score, beta, current_adf
            )
            
            # --- SIGNAL CHECK ---
            signal = 0 # 0: None, 1: Short Spread (Short A), -1: Long Spread (Long A)
            
            if z_score > strategy.z_threshold:
                signal = 1
            elif z_score < -strategy.z_threshold:
                signal = -1
                
            if signal != 0:
                # --- LABELING ---
                # Look ahead 'future_window' bars.
                # If Short Spread (1): We want Spread to DECREASE.
                # If Long Spread (-1): We want Spread to INCREASE.
                
                future_spread = spread_series.iloc[-1] # Current
                # Note: Beta is fixed at entry for PnL calculation assumption
                # Future PnL approx = (Spread_entry - Spread_exit) for Short Spread
                
                future_prices_a = df_a.iloc[i+1 : i+1+future_window]['close']
                future_prices_b = df_b.iloc[i+1 : i+1+future_window]['close']
                
                # Check if any point in future hits profit target
                is_profitable = 0
                
                entry_spread = price_a - beta * price_b
                
                for fa, fb in zip(future_prices_a, future_prices_b):
                    future_spread_val = fa - beta * fb
                    
                    if signal == 1: # Short Spread
                        pnl = entry_spread - future_spread_val
                    else: # Long Spread
                        pnl = future_spread_val - entry_spread
                        
                    # Normalize PnL by Price A
                    ret = pnl / price_a
                    
                    if ret > profit_threshold:
                        is_profitable = 1
                        break
                    # Optional: Check stop loss
                
                # Add to Dataset
                row = features.copy()
                row['Signal_Dir'] = signal
                row['Label'] = is_profitable
                dataset.append(row)
                
    # Save
    df_train = pd.DataFrame(dataset)
    logger.info(f"Generated {len(df_train)} training samples.")
    output_path = os.path.join(os.path.dirname(__file__), 'training_data.csv')
    df_train.to_csv(output_path, index=False)
    logger.info(f"Saved to {output_path}")

if __name__ == "__main__":
    generate_training_data()
