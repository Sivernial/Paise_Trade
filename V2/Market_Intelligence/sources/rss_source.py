import feedparser
import urllib.parse
from datetime import datetime, timedelta
import logging
from typing import List
from ..config import MIConfig
from ..models import IntelligenceSignal, EventType
from ..processors.base_processor import TextProcessor

logger = logging.getLogger(__name__)

class RSSSource:
    
    def __init__(self):
        self.source_name = "GoogleNews"
        self.base_url = MIConfig.RSS_URL
        
    def fetch_signals(self, symbol: str) -> List[IntelligenceSignal]:
        signals = []
        try:
            query = f"{symbol} share news"
            encoded_query = urllib.parse.quote(query)
            url = self.base_url.format(query=encoded_query)
            
            feed = feedparser.parse(url)
            
            if not feed.entries:
                return []
                
            for entry in feed.entries[:5]: # Top 5 only
                title = entry.title
                summary = TextProcessor.clean_text(entry.get('summary', title))
                link = entry.link
                
                # Timestamp
                pub_date = entry.get('published_parsed')
                if pub_date:
                    timestamp = datetime(*pub_date[:6])
                else:
                    timestamp = datetime.now()
                
                # Filter old news (> 24h)
                if (datetime.now() - timestamp) > timedelta(hours=24):
                    continue
                    
                # Process
                event_type = TextProcessor.classify_event(summary + " " + title)
                sent_score, impact_score = TextProcessor.score_sentiment(summary + " " + title)
                
                # Create Signal
                sig = IntelligenceSignal(
                    symbol=symbol,
                    timestamp=timestamp,
                    source=self.source_name,
                    event_type=event_type,
                    sentiment_score=sent_score,
                    impact_score=impact_score,
                    confidence=0.8, # Google Nes is generally reliable
                    summary=title, # Title is often cleaner than summary
                    raw_url=link
                )
                
                signals.append(sig)
                
        except Exception as e:
            logger.error(f"RSS Fetch Error for {symbol}: {e}")
            
        return signals
