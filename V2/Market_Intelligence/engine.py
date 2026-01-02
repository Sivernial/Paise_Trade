import logging
import threading
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from .models import IntelligenceSignal
from .config import MIConfig
from .sources.rss_source import RSSSource
from .storage.repository import MIRepository

logger = logging.getLogger(__name__)

class IntelligenceEngine:
    """
    Main Entry Point for Market Intelligence.
    Orchestrates fetching, processing, and storage.
    """
    
    def __init__(self, db_path: str = None):
        self.repo = MIRepository(db_path)
        self.rss_source = RSSSource()
        self.cache: Dict[str, IntelligenceSignal] = {}
        self.cache_lock = threading.Lock()
        
    def fetch_signals_sync(self, symbol: str) -> Optional[IntelligenceSignal]:
        """
        Blocking fetch. Used for periodic updates or initial load.
        """
        try:
            # 1. Fetch
            signals = self.rss_source.fetch_signals(symbol)
            if not signals: return None
            
            # 2. Store
            self.repo.save_signals(signals)
            
            # 3. Update Cache (Most recent)
            # Find strongest impact or most recent
            latest = sorted(signals, key=lambda x: x.timestamp, reverse=True)[0]
            
            with self.cache_lock:
                self.cache[symbol] = latest
                
            return latest
            
        except Exception as e:
            logger.error(f"Engine Fetch Error {symbol}: {e}")
            return None

    def get_signal(self, symbol: str) -> IntelligenceSignal:
        """
        Fast Retrieval for Trading Loop.
        Returns cached signal or loads from DB.
        If nothing found, returns Neutral signal.
        """
        # 1. Check Memory Cache
        with self.cache_lock:
            if symbol in self.cache:
                sig = self.cache[symbol]
                # Check expiry
                if (datetime.now() - sig.timestamp).total_seconds() < MIConfig.CACHE_EXPIRY:
                    return sig
        
        # 2. Check DB
        db_sig = self.repo.get_latest_signal(symbol)
        if db_sig:
             # Check DB Expiry (e.g. 24 hours) - Relaxed for DB
             if (datetime.now() - db_sig.timestamp).days < 1:
                 with self.cache_lock:
                     self.cache[symbol] = db_sig
                 return db_sig
                 
        # 3. Return Neutral Fallback
        return IntelligenceSignal(
            symbol=symbol,
            timestamp=datetime.now(),
            source="System",
            event_type="GENERAL",
            sentiment_score=0.0,
            impact_score=0.0,
            confidence=0.0,
            summary="No Data"
        )
