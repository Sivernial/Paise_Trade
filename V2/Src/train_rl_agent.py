import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from Backtesting import HistoricalDataFetcher
from login import get_kite_instance
from AI.rl_execution import RLExecutionAgent
from AI.quantformer import QuantformerPredictor
from Common.microstructure import calculate_buying_pressure, calculate_volatility_regime
from Common.quant_utils import calculate_pca_residuals

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
BASKETS = {'Banking': ['SBIN', 'PNB']} # Train on a subset for speed
EPISODES = 50
MAX_STEPS = 12 # Max 1 hour to execute

def train_rl_agent():
    agent = RLExecutionAgent()
    kite = get_kite_instance()
    fetcher = HistoricalDataFetcher(kite)
    
    # 1. Fetch Data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    logger.info("Fetching Training Data...")
    raw_data, resampled_data = fetcher.fetch_and_resample(BASKETS['Banking'], start_date, end_date, "5min", "5min")
    
    if not resampled_data:
        logger.error("No data fetched.")
        return

    # 2. Precompute Features (OFI, Volatility, Signals)
    # Simplified simulation: Assume we want to BUY every time Z < -2.0 (Just to train execution logic)
    
    scenarios = []
    
    for sym in BASKETS['Banking']:
        df = resampled_data[sym]
        df['ofi'] = calculate_buying_pressure(df)
        df['vol_ratio'] = calculate_volatility_regime(df)
        
        # Fake Signal Generation (Z-score proxy)
        df['log_ret'] = np.log(df['close'] / df['close'].shift(1))
        df['z_score'] = (df['close'] - df['close'].rolling(50).mean()) / df['close'].rolling(50).std()
        
        # Identify "Arrival" points (e.g. Z < -2 for BUY)
        entry_indices = df[df['z_score'] < -2.0].index
        
        for idx in entry_indices:
            # Check availability of future data
            loc = df.index.get_loc(idx)
            if loc + MAX_STEPS < len(df):
                scenarios.append({
                    'sym': sym,
                    'start_idx': loc,
                    'direction': 1 # BUY
                })
                
    logger.info(f"Generated {len(scenarios)} Execution Scenarios.")
    
    # 3. Training Loop
    total_reward = 0
    
    for ep in range(EPISODES):
        np.random.shuffle(scenarios)
        epoch_reward = 0
        
        for scen in scenarios[:100]: # Sample batch
            sym = scen['sym']
            df = resampled_data[sym]
            start_loc = scen['start_idx']
            direction = scen['direction'] # 1=Buy
            
            arrival_price = df.iloc[start_loc]['close']
            
            # State: [Z, Prob(Dummy), OFI, Vol, Time]
            # Init State
            curr_loc = start_loc
            filled = False
            fill_price = 0.0
            
            for step in range(MAX_STEPS):
                row = df.iloc[curr_loc]
                
                state = np.array([
                    row['z_score'],
                    0.5, # Dummy Prob
                    row['ofi'],
                    row['vol_ratio'],
                    1.0 - (step / MAX_STEPS) # Time Remaining
                ])
                
                action = agent.get_action(state)
                
                reward = 0
                done = False
                
                # Execute Action
                if action == 1: # MARKET
                    slippage = row['close'] * 0.0005 # 5bps
                    fill_price = row['close'] + slippage
                    filled = True
                    
                elif action == 2: # LIMIT (Passive - try to catch Low)
                    # Checking next bar for fill
                    if curr_loc + 1 < len(df):
                        next_bar = df.iloc[curr_loc + 1]
                        # If Low < Limit Price (Current Close), we fill
                        if next_bar['low'] < row['close']:
                            fill_price = row['close'] # Filled at limit
                            filled = True
                        else:
                            # Not filled, penalty for waiting? or just continue
                            pass
                    else:
                        filled = False # End of data
                        
                elif action == 0: # WAIT
                    pass
                
                # Force Fill at End
                if step == MAX_STEPS - 1 and not filled:
                    fill_price = row['close'] # Force Market
                    filled = True
                    
                # Calculate Reward if Filled
                if filled:
                    # Reward = (Arrival - Fill) for Buy -> Positive if Fill < Arrival
                    pnl_bps = (arrival_price - fill_price) / arrival_price * 10000 * direction
                    
                    # Reward: Alpha Capture + Execution Quality
                    # Bonus for Market fill (Action 1) if PnL is positive
                    reward = pnl_bps + (5.0 if action == 1 and pnl_bps > 0 else 0)
                    done = True
                else:
                    reward = -0.5 # Increased penalty for hesitation (Waiting/Missing)
                    
                # Creating Signals for next state (approx)
                if not done and curr_loc + 1 < len(df):
                    next_row = df.iloc[curr_loc+1]
                    next_state = np.array([
                         next_row['z_score'], 0.5, next_row['ofi'], next_row['vol_ratio'], 
                         1.0 - ((step+1)/MAX_STEPS)
                    ])
                else:
                    next_state = np.zeros(5)
                    
                agent.update(state, action, reward, next_state, done)
                epoch_reward += reward
                
                if done:
                    break
                    
                curr_loc += 1
                
        logger.info(f"Episode {ep+1} Total ROI (Reward): {epoch_reward:.2f}")
        
    agent.save()
    logger.info("RL Training Complete.")

if __name__ == "__main__":
    train_rl_agent()
