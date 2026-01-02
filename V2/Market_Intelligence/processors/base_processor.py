import re
import hashlib
from typing import Tuple, List
from ..config import MIConfig
from ..models import EventType

class TextProcessor:
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Remove HTML, extra spaces, normalization"""
        if not text: return ""
        text = re.sub(r'<[^>]+>', '', text) # Strip HTML
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    @staticmethod
    def generate_hash(text: str) -> str:
        """Unique ID for deduplication"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    @staticmethod
    def classify_event(text: str) -> EventType:
        """Classify text into event types based on keywords"""
        text_lower = text.lower()
        
        for event, keywords in MIConfig.KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    try:
                        return EventType(event)
                    except:
                        pass
                        
        return EventType.GENERAL

    @staticmethod
    def score_sentiment(text: str) -> Tuple[float, float]:
        """
        Returns (sentiment_score, impact_score)
        Simple lexicon-based approach. source for V1.
        """
        text_lower = text.lower()
        
        bull_count = sum(1 for w in MIConfig.BULLISH if w in text_lower)
        bear_count = sum(1 for w in MIConfig.BEARISH if w in text_lower)
        
        total = bull_count + bear_count
        if total == 0:
            return 0.0, 0.0 # Neutral, Low Impact
            
        # Sentiment (-1 to 1)
        sentiment = (bull_count - bear_count) / total
        
        # Impact (0 to 1) based on intensity of keywords
        # More keywords = Higher confidence/impact potential
        impact = min(1.0, total / 5.0) 
        
        return sentiment, impact
