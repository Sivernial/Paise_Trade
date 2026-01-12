"""
Training script for AI Validator.
Collects features from historical backtests and trains a binary classifier.
"""
import sys
import os
import pandas as pd
import numpy as np
import joblib
import logging
from datetime import datetime, timedelta
from typing import List, Tuple

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Algorithms import PairTradingStrategy
from Backtesting import HistoricalDataFetcher
from Backtesting.config import StrategyConfig
from login import get_kite_instance
from AI.ai_validator import AIValidator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TrainAI")

def collect_training_data(days: int = 60) -> pd.DataFrame:
    """
    Runs a backtest and collects features/outcomes for each candidate signal.
    """
    config = StrategyConfig.INTRADAY_PAIR_TRADING
    kite = get_kite_instance()
    if not kite: return pd.DataFrame()
    
    fetcher = HistoricalDataFetcher(kite)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    symbols = list(set([p[0] for p in config['pairs']] + [p[1] for p in config['pairs']]))
    _, data = fetcher.fetch_and_resample(symbols, start_date, end_date, "5min", "5min")
    
    strategy = PairTradingStrategy(config)
    # Ensure KF matches runner
    for pair in strategy.pairs:
        from Common.quant_utils import KalmanFilterReg
        strategy.kf_registry[pair] = KalmanFilterReg(delta=1e-6, R=1e-4)

    training_samples = []
    
    # Get common timeline
    timeline = None
    for sym in data:
        if timeline is None: timeline = data[sym].index
        else: timeline = timeline.intersection(data[sym].index)
    
    logger.info(f"Starting data collection over {len(timeline)} bars...")
    
    for i, current_time in enumerate(timeline):
        data_slice = {s: data[s][data[s].index <= current_time] for s in data}
        
        # We need a custom hook to extract features EVEN if filters reject (for training diversity)
        # But for now, we'll just extract features when BOTH thresholds are crossed
        
        # Step the strategy
        signals = strategy.generate_signals(data_slice, current_time)
        
        for pair_key in strategy.pairs:
            asset_a, asset_b = pair_key
            state = strategy.latest_state.get(pair_key)
            if not state: continue
            
            spread = state['spread']
            up = state['dynamic_thresh_upper']
            low = state['dynamic_thresh_lower']
            
            # If spread is outside bands (Candidate Signal)
            if spread > up or spread < low:
                # Extract features used by AIValidator
                features = strategy.ai_validator.extract_features(
                    data_slice[asset_a]['close'] - state['beta'] * data_slice[asset_b]['close'], # spread_series (naive)
                    state['beta'],
                    state['rsi'],
                    state['hurst'],
                    state['bias']
                )
                
                # LOOK AHEAD for Label (Target)
                # Success = Spread reverts to mu_adj within 20 bars without hitting 2.5*ATR stop
                outcome = label_trade(data, pair_key, state['beta'], i, timeline, 
                                    target=state.get('mu_adj', 0), 
                                    stop_dist=2.5 * state['atr'],
                                    is_short=(spread > up))
                
                if outcome is not None:
                    features['target'] = outcome
                    training_samples.append(features)
                    
        if i % 100 == 0:
            logger.info(f"Processed bar {i}/{len(timeline)}... Samples: {len(training_samples)}")
            
    return pd.DataFrame(training_samples)

def label_trade(all_data, pair_key, beta, current_idx, timeline, target, stop_dist, is_short, horizon=30):
    """
    Look ahead to see if the trade was successful.
    1.0: Hit target (reversion)
    0.0: Hit stop loss or timed out
    """
    asset_a, asset_b = pair_key
    start_spread = all_data[asset_a]['close'].iloc[current_idx] - beta * all_data[asset_b]['close'].iloc[current_idx]
    
    for j in range(1, horizon):
        if current_idx + j >= len(timeline): break
        
        future_time = timeline[current_idx + j]
        price_a = all_data[asset_a].loc[future_time, 'close']
        price_b = all_data[asset_b].loc[future_time, 'close']
        future_spread = price_a - beta * price_b
        
        move = future_spread - start_spread
        loss = move if is_short else -move
        
        # 1. Check Stop Loss
        if loss > stop_dist:
            return 0.0
            
        # 2. Check Target (Mean Reversion)
        if is_short and future_spread <= target:
            return 1.0
        if not is_short and future_spread >= target:
            return 1.0
            
    return 0.0 # Time out is treated as failure/neutral for conservative training

def train_model(df: pd.DataFrame):
    if df.empty:
        logger.error("No training data collected.")
        return
        
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report
    
    X = df.drop(columns=['target'])
    y = df['target']
    
    logger.info(f"Training on {len(df)} samples. Class Balance: {y.mean():.2%}")
    
    if len(df) < 10:
        logger.warning("Too few samples to train meaningful model.")
        return

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    logger.info("\n" + classification_report(y_test, y_pred))
    
    model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "AI", "model.joblib")
    joblib.dump(model, model_path)
    logger.info(f"✅ Model saved to {model_path}")

if __name__ == "__main__":
    data_df = collect_training_data(days=40)
    train_model(data_df)
