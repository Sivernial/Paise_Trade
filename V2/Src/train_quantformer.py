import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from datetime import datetime, timedelta
import logging
from AI.quantformer import Quantformer, QuantformerPredictor
from Common.quant_utils import calculate_pca_residuals
from Backtesting import HistoricalDataFetcher
from login import get_kite_instance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
SEQ_LEN = 30
BATCH_SIZE = 64
EPOCHS = 10
LEARNING_RATE = 0.001

BASKETS = {
    'Banking': ['SBIN', 'PNB', 'BANKBARODA', 'CANBK', 'IDFCFIRSTB'],
    'IT': ['INFY', 'TCS', 'HCLTECH', 'TECHM', 'WIPRO'],
    'Auto': ['MARUTI', 'M&M', 'TMPV', 'BAJAJ-AUTO', 'EICHERMOT'],
    'Pharma': ['SUNPHARMA', 'CIPLA', 'DRREDDY', 'DIVISLAB']
}

class FinancialDataset(Dataset):
    def __init__(self, sequences, targets):
        self.sequences = torch.FloatTensor(sequences)
        self.targets = torch.FloatTensor(targets).unsqueeze(1)
        
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        return self.sequences[idx], self.targets[idx]

def create_sequences(df, target, seq_len):
    xs = []
    ys = []
    for i in range(len(df) - seq_len):
        x = df.iloc[i:(i+seq_len)].values
        y = target.iloc[i+seq_len]
        xs.append(x)
        ys.append(y)
    return np.array(xs), np.array(ys)

def train_quantformer():
    kite = get_kite_instance()
    fetcher = HistoricalDataFetcher(kite)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)
    
    all_sequences = []
    all_targets = []
    
    # 1. Data Collection & Feature Engineering
    for sector, symbols in BASKETS.items():
        logger.info(f"Processing Sector: {sector}")
        processed_data = fetcher.fetch_and_resample(symbols, start_date, end_date, "5min", "5min")
        
        # Align Data
        common_idx = None
        valid_data = {}
        if not processed_data: continue
            
        for s in symbols:
            if s in processed_data[1]:
                 valid_data[s] = processed_data[1][s]
        
        if not valid_data: continue
            
        prices = pd.DataFrame({s: valid_data[s]['close'] for s in symbols}).dropna()
        volumes = pd.DataFrame({s: valid_data[s]['volume'] for s in symbols}).dropna()
        
        if prices.empty: continue
            
        # PCA Residuals
        log_rets = np.log(prices / prices.shift(1)).dropna()
        residuals = calculate_pca_residuals(log_rets, n_components=1)
        cum_residuals = residuals.cumsum()
        
        # Create Features per symbol
        for sym in symbols:
            if sym not in cum_residuals.columns: continue
                
            df = pd.DataFrame()
            df['res'] = cum_residuals[sym]
            df['res_lag1'] = df['res'].shift(1)
            df['vol'] = log_rets[sym].rolling(10).std()
            df['volume'] = volumes[sym]
             # Normalize Volume
            df['volume'] = df['volume'] / df['volume'].rolling(50).mean()
            df['res_ma'] = df['res'].rolling(20).mean()
            
            # Target (Next 3 bars return sign)
            target_diff = df['res'].shift(-3) - df['res']
            target_class = (target_diff > 0).astype(int) # 1 if Up, 0 if Down
            
            df = df.dropna()
            target_series = target_class.loc[df.index]
            
            # Drop target NaNs (end of series)
            valid_idx = target_series.dropna().index
            df = df.loc[valid_idx]
            target_series = target_series.loc[valid_idx]
            
            # Normalize Features (Z-Score)
            df = (df - df.mean()) / (df.std() + 1e-6)
            
            # Create Sequences
            if len(df) > SEQ_LEN:
                seqs, targs = create_sequences(df, target_series, SEQ_LEN)
                all_sequences.append(seqs)
                all_targets.append(targs)
                
    if not all_sequences:
        logger.error("No data collected.")
        return

    X = np.concatenate(all_sequences)
    y = np.concatenate(all_targets)
    
    # Classification: Targets must be LongTensor
    dataset = FinancialDataset(X, y)
    dataset.targets = torch.LongTensor(y) # Override with Long for CE Loss
    
    dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)
    
    # 2. Model Setup
    device = torch.device('mps' if torch.backends.mps.is_available() else 'cpu')
    logger.info(f"Training on {device}, Samples: {len(X)}")
    
    model = Quantformer(input_dim=X.shape[2]).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    
    # 3. Training Loop
    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0
        correct = 0
        total = 0
        
        for batch_X, batch_y in dataloader:
            batch_X, batch_y = batch_X.to(device), batch_y.to(device)
            
            optimizer.zero_grad()
            output = model(batch_X)
            loss = criterion(output, batch_y)
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            
            # Accuracy
            _, predicted = torch.max(output.data, 1)
            total += batch_y.size(0)
            correct += (predicted == batch_y).sum().item()
            
        avg_loss = total_loss / len(dataloader)
        accuracy = 100 * correct / total
        logger.info(f"Epoch {epoch+1}/{EPOCHS} | Loss: {avg_loss:.6f} | Acc: {accuracy:.2f}%")
        
    # 4. Save
    predictor = QuantformerPredictor(input_dim=X.shape[2], seq_len=SEQ_LEN)
    predictor.model = model
    predictor.save()
    logger.info("Quantformer Classification Training Complete.")

if __name__ == "__main__":
    train_quantformer()
