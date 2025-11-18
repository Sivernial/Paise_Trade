import sqlite3
from contextlib import contextmanager
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class DatabaseConnection:
    def __init__(self, db_path: str = "trading_data_v2.db"):
        self.db_path = db_path
        self._init_database()
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def _init_database(self):
        with self.get_connection() as conn:
            conn.executescript('''
                CREATE TABLE IF NOT EXISTS historical_candles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume INTEGER NOT NULL,
                    interval TEXT NOT NULL,
                    UNIQUE(symbol, timestamp, interval)
                );
                
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    entry_time TEXT NOT NULL,
                    exit_time TEXT,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    quantity INTEGER NOT NULL,
                    side TEXT NOT NULL,
                    pnl REAL,
                    strategy TEXT,
                    mode TEXT
                );
                
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT UNIQUE,
                    symbol TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL,
                    order_type TEXT NOT NULL,
                    transaction_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    filled_quantity INTEGER,
                    average_price REAL
                );
                
                CREATE INDEX IF NOT EXISTS idx_candles_symbol 
                ON historical_candles(symbol, timestamp);
                
                CREATE INDEX IF NOT EXISTS idx_trades_symbol 
                ON trades(symbol, entry_time);
                
                CREATE INDEX IF NOT EXISTS idx_orders_symbol 
                ON orders(symbol, timestamp);
            ''')

