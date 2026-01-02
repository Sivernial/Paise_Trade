import sqlite3
import json
import logging
from typing import List, Optional
from datetime import datetime
from ..models import IntelligenceSignal
import os

logger = logging.getLogger(__name__)

class MIRepository:
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Default to V2/trading_data_v2.db
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.db_path = os.path.join(base_dir, 'trading_data_v2.db')
        else:
            self.db_path = db_path
            
    def get_connection(self):
        return sqlite3.connect(self.db_path)
        
    def save_signals(self, signals: List[IntelligenceSignal]):
        if not signals: return
        
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            for sig in signals:
                # Check duplication by symbol + timestamp + source (rough) or just insert
                # We'll just insert and rely on downstream query limiting
                cursor.execute("""
                    INSERT INTO market_intelligence_signals 
                    (symbol, signal_timestamp, event_type, sentiment_score, impact_score, summary, source) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    sig.symbol, 
                    sig.timestamp.isoformat(), 
                    sig.event_type.value, 
                    sig.sentiment_score, 
                    sig.impact_score, 
                    sig.summary, 
                    sig.source
                ))
            conn.commit()
        except Exception as e:
            logger.error(f"DB Save Error: {e}")
        finally:
            conn.close()

    def get_latest_signal(self, symbol: str) -> Optional[IntelligenceSignal]:
        """Get the most recent signal for valid cache"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT symbol, signal_timestamp, event_type, sentiment_score, impact_score, summary, source 
                FROM market_intelligence_signals 
                WHERE symbol = ? 
                ORDER BY signal_timestamp DESC LIMIT 1
            """, (symbol,))
            
            row = cursor.fetchone()
            if row:
                return IntelligenceSignal(
                    symbol=row[0],
                    timestamp=datetime.fromisoformat(row[1]),
                    event_type=row[2],
                    sentiment_score=row[3],
                    impact_score=row[4],
                    confidence=0.8, # hardcoded for retrieval
                    summary=row[5],
                    source=row[6]
                )
            return None
        except Exception as e:
            logger.error(f"DB Read Error: {e}")
            return None
        finally:
            conn.close()
