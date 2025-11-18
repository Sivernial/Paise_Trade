from datetime import datetime
from typing import List, Optional
import pandas as pd
from .connection import DatabaseConnection

class CandleRepository:
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
    
    def save_candles(self, candles: List[dict], interval: str = "1day"):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            for candle in candles:
                cursor.execute('''
                    INSERT OR REPLACE INTO historical_candles 
                    (symbol, timestamp, open, high, low, close, volume, interval)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    candle['symbol'],
                    candle['timestamp'].isoformat(),
                    candle['open'],
                    candle['high'],
                    candle['low'],
                    candle['close'],
                    candle['volume'],
                    interval
                ))
    
    def get_candles(self, symbol: str, start_date: datetime, 
                   end_date: datetime, interval: str = "1day") -> pd.DataFrame:
        with self.db.get_connection() as conn:
            query = '''
                SELECT * FROM historical_candles 
                WHERE symbol = ? AND interval = ? 
                AND timestamp BETWEEN ? AND ?
                ORDER BY timestamp
            '''
            df = pd.read_sql_query(query, conn, params=[
                symbol, interval, 
                start_date.isoformat(), 
                end_date.isoformat()
            ])
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
            return df
    
    def has_data(self, symbol: str, start_date: datetime, 
                end_date: datetime, interval: str = "1day") -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM historical_candles 
                WHERE symbol = ? AND interval = ? 
                AND timestamp BETWEEN ? AND ?
            ''', (symbol, interval, start_date.isoformat(), end_date.isoformat()))
            count = cursor.fetchone()[0]
            expected_days = (end_date - start_date).days
            return count > expected_days * 0.8

