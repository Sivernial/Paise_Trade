"""
Configuration settings for V5 trading system.
"""
import os
from dataclasses import dataclass

@dataclass
class TradingConfig:
    """Core trading configuration."""
    INITIAL_CAPITAL: float = 100000
    COMMISSION_RATE: float = 0.0003  # 0.03%
    SLIPPAGE_RATE: float = 0.0001    # 0.01%

@dataclass
class DataConfig:
    """Data fetching configuration."""
    INTERVAL: str = "5min"
    WARMUP_DAYS: int = 15
    LOOKBACK_WINDOW: int = 200

@dataclass
class RiskConfig:
    """Risk management parameters."""
    MAX_POSITION_SIZE: float = 0.50  # 50% of capital per position
    DAILY_LOSS_LIMIT: float = 0.02  # 2% daily loss limit
    
    # SBIN-specific
    SBIN_PROFIT_TARGET: float = 0.01  # 1.0%
    SBIN_STOP_LOSS: float = 0.005     # 0.5%

# Environment paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
