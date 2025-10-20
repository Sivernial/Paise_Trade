"""
Dataclasses for Strategy Framework
Contains all data structures used in the strategy module
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

@dataclass
class Signal:
    """Trading signal with metadata"""
    symbol: str
    signal_type: SignalType
    confidence: float  # 0.0 to 1.0
    price: float
    timestamp: datetime
    reason: str = ""
    indicators: Optional[Dict[str, float]] = None