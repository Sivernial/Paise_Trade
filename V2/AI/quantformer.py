import torch
import torch.nn as nn
import numpy as np
import logging
import os

logger = logging.getLogger(__name__)

class Quantformer(nn.Module):
    """
    Time-Series Transformer for Alpha Prediction.
    Architecture: Input Embedding -> Positional Encoding -> Transformer Encoder -> MLP Head
    """
    def __init__(self, input_dim: int = 5, d_model: int = 64, nhead: int = 4, 
                 num_layers: int = 2, dropout: float = 0.1):
        super(Quantformer, self).__init__()
        
        self.model_type = 'Transformer'
        self.input_dim = input_dim
        self.d_model = d_model
        
        # 1. Feature Embedding (Project input to d_model)
        self.embedding = nn.Linear(input_dim, d_model)
        
        # 2. Positional Encoding (Learnable)
        self.pos_encoder = nn.Parameter(torch.zeros(1, 100, d_model)) # Max seq len 100
        
        # 3. Transformer Encoder
        encoder_layers = nn.TransformerEncoderLayer(d_model, nhead, dim_feedforward=d_model*4, dropout=dropout, batch_first=True)
        self.transformer_encoder = nn.TransformerEncoder(encoder_layers, num_layers)
        
        # 4. Output Head (Classification: Down=0, Up=1)
        self.decoder = nn.Sequential(
            nn.Linear(d_model, 32),
            nn.ReLU(),
            nn.Linear(32, 2) 
        )
        
        self.init_weights()

    def init_weights(self):
        initrange = 0.1
        self.embedding.bias.data.zero_()
        self.embedding.weight.data.uniform_(-initrange, initrange)
        self.decoder[0].bias.data.zero_()
        self.decoder[0].weight.data.uniform_(-initrange, initrange)

    def forward(self, src):
        # src shape: [batch_size, seq_len, input_dim]
        src = self.embedding(src) 
        seq_len = src.size(1)
        src = src + self.pos_encoder[:, :seq_len, :]
        output = self.transformer_encoder(src) 
        last_token = output[:, -1, :] 
        logits = self.decoder(last_token) # [batch, 2]
        return logits

class QuantformerPredictor:
    """
    Wrapper for Quantformer training and inference.
    """
    def __init__(self, model_path: str = "AI/v4_quantformer.pth", input_dim=5, seq_len=30):
        self.model_path = model_path
        self.input_dim = input_dim
        self.seq_len = seq_len
        self.device = torch.device('mps' if torch.backends.mps.is_available() else 'cpu')
        
        self.model = Quantformer(input_dim=input_dim, d_model=64).to(self.device)
        
    def save(self):
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'input_dim': self.input_dim,
            'seq_len': self.seq_len
        }, self.model_path)
        logger.info(f"Quantformer saved to {self.model_path}")

    def load(self):
        if os.path.exists(self.model_path):
            checkpoint = torch.load(self.model_path, map_location=self.device)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.model.eval()
            logger.info("Quantformer loaded.")
        else:
            logger.warning("Quantformer model not found.")

    def prepare_sequence(self, df: 'pd.DataFrame') -> torch.Tensor:
        """Converts DataFrame features to Tensor sequence."""
        if len(df) < self.seq_len:
            return None
        seq = df.tail(self.seq_len).values
        return torch.FloatTensor(seq).unsqueeze(0).to(self.device)

    def predict(self, features_df: 'pd.DataFrame') -> float:
        """Returns Probability of UP move (Class 1)"""
        self.model.eval()
        with torch.no_grad():
            tensor_seq = self.prepare_sequence(features_df)
            if tensor_seq is None:
                return 0.5
            
            logits = self.model(tensor_seq)
            probs = torch.softmax(logits, dim=1)
            return probs[0, 1].item() # Return Prob(Up)
