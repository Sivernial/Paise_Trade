
import sys
import os
import joblib

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
from Common.pair_scanner import scan_pairs, SECTORS
from login import get_kite_instance
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sector Mapping
SECTOR_MAP = {k: i+1 for i, k in enumerate(sorted(SECTORS.keys()))}

def get_sector_id(sym_a, sym_b):
    sec_a = "OTHER"
    for sec, syms in SECTORS.items():
        if sym_a in syms:
            sec_a = sec
            break
    return SECTOR_MAP.get(sec_a, 0)

def generate_sequences(data, time_steps=60):
    """
    Convert 2D array [samples, features] to 3D array [samples, time_steps, features]
    """
    X, y = [], []
    # Data is list of rows (dicts)
    # We need to process per pair
    pass

def generate_deep_training_data():
    kite = get_kite_instance()
    fetcher = HistoricalDataFetcher(kite)
    
    # 1. Pipeline: Scan Pairs
    logger.info("Scanning for pairs...")
    scanned_df = scan_pairs(days=120)
    
    if scanned_df is None or scanned_df.empty:
        pairs = [('ACC', 'AMBUJACEM'), ('INFY', 'TCS')]
    else:
        top_pairs_df = scanned_df.head(50)
        pairs = list(zip(top_pairs_df['Asset A'], top_pairs_df['Asset B']))

    lookback_days = 90 # Need more history for sequences
    future_window = 12
    profit_threshold = 0.005
    sequence_length = 30 # LSTM Lookback Window
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)
    
    all_sequences = []
    all_labels = []
    
    # We need to collect ALL features first to fit scalers? 
    # Or just save raw sequences and scale during training.
    # Let's save raw sequences in a very efficient format (numpy or joblib)
    
    total_samples = 0
    
    for asset_a, asset_b in pairs:
        logger.info(f"Processing {asset_a}-{asset_b} for Deep Learning...")
        
        try:
            result = fetcher.fetch_and_resample(
                [asset_a, asset_b], start_date, end_date, 
                MarketDataConfig.FETCH_INTERVAL, MarketDataConfig.SIGNAL_INTERVAL
            )
            
            if not result or len(result) < 2: continue
            data = result[1]
            if asset_a not in data or asset_b not in data: continue
            
            # Align lengths
            min_len = min(len(data[asset_a]), len(data[asset_b]))
            df_a = data[asset_a].iloc[-min_len:]
            df_b = data[asset_b].iloc[-min_len:]
            
            # Init Strategy for logic
            strategy = PairTradingStrategy({'pairs': [(asset_a, asset_b)]})
            
            # Pre-calculate features row by row to build history
            pair_features = []
            pair_labels = []
            
            warmup = 50
            sector_id = get_sector_id(asset_a, asset_b)
            
            for i in range(warmup, len(df_a) - future_window):
                window_a = df_a.iloc[:i+1]
                window_b = df_b.iloc[:i+1]
                
                # --- LOGIC ---
                kf = strategy.kf_registry[(asset_a, asset_b)]
                price_a = window_a.iloc[-1]['close']
                price_b = window_b.iloc[-1]['close']
                beta = kf.update(price_a, price_b)
                
                spread_series = window_a['close'] - beta * window_b['close']
                
                # Optimized Z-Score
                mean = spread_series.rolling(strategy.lookback).mean().iloc[-1]
                std = spread_series.rolling(strategy.lookback).std().iloc[-1]
                
                if std == 0: continue
                z_score = (spread_series.iloc[-1] - mean) / std
                
                # Features
                feats = FeatureEngineer.extract_features(
                    window_a, window_b, spread_series, z_score, beta, -3.0, sector_id
                )
                
                # Convert to list (ordered)
                feat_vec = list(feats.values()) 
                pair_features.append(feat_vec)
                
                # Labeling (Profitibility of entry at this step)
                # We label EVERY step for the LSTM to learn general dynamics,
                # NOT just when Z > 2. This is "Trend Prediction".
                
                future_prices_a = df_a.iloc[i+1 : i+1+future_window]['close']
                future_prices_b = df_b.iloc[i+1 : i+1+future_window]['close']
                
                entry_spread = price_a - beta * price_b
                is_profitable = 0
                
                # Check Long entry profitability (Mean Reversion from Low Z)
                # Check Short entry profitability (Mean Reversion from High Z)
                # Simplified: Label 1 if spread REVERTS towards mean?
                # Paper says "Trend Prediction". Let's stick to our "Signal Profitability" concept
                # but applied to all steps? No, that confuses the model.
                # Let's label: Will spread GO UP (1) or DOWN (0)? 
                # Or Multi-class: Up, Down, Neutral.
                
                # Shen et al: "Trend Prediction"
                # Let's predict: Will price A outperform B adjusted by Beta? (Spread direction)
                future_spread = future_prices_a.iloc[-1] - beta * future_prices_b.iloc[-1]
                delta = future_spread - entry_spread
                
                label = 1 if delta > 0 else 0 # 1=Spread Widens, 0=Spread Narrows
                pair_labels.append(label)

            # Create Sequences
            # X Shape: (Samples, Sequence_Length, Num_Features)
            if len(pair_features) > sequence_length:
                X_pair = []
                y_pair = []
                for j in range(len(pair_features) - sequence_length):
                    seq = pair_features[j : j+sequence_length]
                    X_pair.append(seq)
                    y_pair.append(pair_labels[j+sequence_length-1]) # Label for the last step
                
                all_sequences.extend(X_pair)
                all_labels.extend(y_pair)
                total_samples += len(X_pair)
                
        except Exception as e:
            logger.error(f"Error {asset_a}-{asset_b}: {e}")
            continue

    # Save as Numpy Arrays
    logger.info(f"Generated {total_samples} sequences.")
    X_data = np.array(all_sequences)
    y_data = np.array(all_labels)
    
    save_dir = os.path.dirname(__file__)
    np.save(os.path.join(save_dir, 'X_deep.npy'), X_data)
    np.save(os.path.join(save_dir, 'y_deep.npy'), y_data)
    logger.info(f"Saved to X_deep.npy {X_data.shape} and y_deep.npy {y_data.shape}")

if __name__ == "__main__":
    generate_deep_training_data()
