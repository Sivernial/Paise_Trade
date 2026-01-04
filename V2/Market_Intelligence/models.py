from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum
import uuid

class EventType(str, Enum):
    EARNINGS = "EARNINGS"
    MACRO = "MACRO"
    MERGER = "MERGER"
    SCANDAL = "SCANDAL"
    REGULATORY = "REGULATORY"
    PRICE_ACTION = "PRICE_ACTION"
    GENERAL = "GENERAL"

class IntelligenceSignal(BaseModel):
    """
    Standardized Output Contract for Market Intelligence
    """
    signal_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    timestamp: datetime
    source: str
    event_type: EventType = EventType.GENERAL
    
    # Core Signals
    sentiment_score: float = Field(..., ge=-1.0, le=1.0) # -1 (Bearish) to 1 (Bullish)
    impact_score: float = Field(..., ge=0.0, le=1.0)     # 0 (Noise) to 1 (Market Moving)
    confidence: float = Field(..., ge=0.0, le=1.0)       # Source credibility
    
    validity_window_minutes: int = 120
    risk_flags: List[str] = []
    
    summary: str
    raw_url: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
