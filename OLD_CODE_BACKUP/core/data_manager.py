"""
Enhanced Data Management System for Algo Trading
Handles historical data, real-time feeds, and data storage using Zerodha Kite API
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import sqlite3
import os
from kiteconnect import KiteConnect
import logging

class DataManager:
    """
    Comprehensive data management for algorithmic trading
    Features:
    - Historical data fetching from Zerodha API
    - Real-time data handling
    - Local caching and storage
    - Data preprocessing and cleaning
    - Multiple timeframe support
    """
    
    def __init__(self, kite: KiteConnect, db_path: str = "trading_data.db"):
        self.kite = kite
        self.db_path = db_path
        self.logger = self._setup_logger()
        self._init_database()
        
        # Supported intervals by Zerodha
        self.intervals = {
            '1min': 'minute',
            '3min': '3minute', 
            '5min': '5minute',
            '10min': '10minute',
            '15min': '15minute',
            '30min': '30minute',
            '1hour': '60minute',
            '1day': 'day'
        }
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logging for data operations"""
        logger = logging.getLogger('DataManager')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _init_database(self):
        """Initialize SQLite database for local data storage"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS historical_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instrument_token INTEGER,
                    symbol TEXT,
                    interval TEXT,
                    date TEXT,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume INTEGER,
                    oi INTEGER,
                    timestamp TEXT,
                    UNIQUE(instrument_token, interval, date)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS instruments (
                    instrument_token INTEGER PRIMARY KEY,
                    exchange_token INTEGER,
                    tradingsymbol TEXT,
                    name TEXT,
                    last_price REAL,
                    expiry TEXT,
                    strike REAL,
                    tick_size REAL,
                    lot_size INTEGER,
                    instrument_type TEXT,
                    segment TEXT,
                    exchange TEXT
                )
            ''')
            
            conn.commit()
    
    def get_instruments(self, exchange: str = None) -> pd.DataFrame:
        """
        Fetch and cache instrument list from Zerodha
        
        Args:
            exchange: Specific exchange (NSE, BSE, etc.)
        
        Returns:
            DataFrame with instrument details
        """
        try:
            instruments = self.kite.instruments(exchange)
            df = pd.DataFrame(instruments)
            
            # Cache instruments in database
            with sqlite3.connect(self.db_path) as conn:
                df.to_sql('instruments', conn, if_exists='replace', index=False)
            
            self.logger.info(f"Fetched {len(df)} instruments from {exchange or 'all exchanges'}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching instruments: {e}")
            # Return cached data if API fails
            return self._get_cached_instruments()
    
    def _get_cached_instruments(self) -> pd.DataFrame:
        """Get cached instruments from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                return pd.read_sql('SELECT * FROM instruments', conn)
        except:
            return pd.DataFrame()
    
    def get_instrument_token(self, symbol: str, exchange: str = "NSE") -> Optional[int]:
        """
        Get instrument token for a symbol
        
        Args:
            symbol: Trading symbol (e.g., 'RELIANCE')
            exchange: Exchange name
            
        Returns:
            Instrument token or None if not found
        """
        instruments = self._get_cached_instruments()
        if instruments.empty:
            instruments = self.get_instruments()
        
        filtered = instruments[
            (instruments['tradingsymbol'] == symbol) & 
            (instruments['exchange'] == exchange)
        ]
        
        if not filtered.empty:
            return int(filtered.iloc[0]['instrument_token'])
        
        self.logger.warning(f"Instrument token not found for {symbol}:{exchange}")
        return None
    
    def get_historical_data(self, 
                          instrument_token: int,
                          interval: str,
                          from_date: Union[str, datetime],
                          to_date: Union[str, datetime],
                          symbol: str = None,
                          force_refresh: bool = False) -> pd.DataFrame:
        """
        Fetch historical data with intelligent caching
        
        Args:
            instrument_token: Zerodha instrument token
            interval: Data interval (1min, 5min, 1day, etc.)
            from_date: Start date
            to_date: End date
            symbol: Symbol name for caching
            force_refresh: Force API call instead of using cache
            
        Returns:
            DataFrame with OHLCV data
        """
        
        # Convert dates to datetime if strings
        if isinstance(from_date, str):
            from_date = pd.to_datetime(from_date)
        if isinstance(to_date, str):
            to_date = pd.to_datetime(to_date)
        
        # Check cache first (unless force refresh)
        if not force_refresh:
            cached_data = self._get_cached_data(instrument_token, interval, from_date, to_date)
            if not cached_data.empty:
                self.logger.info(f"Using cached data for {symbol or instrument_token}")
                return cached_data
        
        try:
            # Fetch from Zerodha API
            records = self.kite.historical_data(
                instrument_token=instrument_token,
                from_date=from_date,
                to_date=to_date,
                interval=self.intervals.get(interval, interval)
            )
            
            if not records:
                self.logger.warning(f"No data returned for {symbol or instrument_token}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(records)
            df['instrument_token'] = instrument_token
            df['symbol'] = symbol or str(instrument_token)
            df['interval'] = interval
            
            # Cache the data
            self._cache_data(df)
            
            self.logger.info(f"Fetched {len(df)} records for {symbol or instrument_token}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error fetching historical data: {e}")
            return pd.DataFrame()
    
    def _get_cached_data(self, instrument_token: int, interval: str, 
                        from_date: datetime, to_date: datetime) -> pd.DataFrame:
        """Get cached historical data from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = '''
                    SELECT * FROM historical_data 
                    WHERE instrument_token = ? AND interval = ? 
                    AND date >= ? AND date <= ?
                    ORDER BY date
                '''
                
                df = pd.read_sql(query, conn, params=[
                    instrument_token, interval, 
                    from_date.strftime('%Y-%m-%d'),
                    to_date.strftime('%Y-%m-%d')
                ])
                
                if not df.empty:
                    df['date'] = pd.to_datetime(df['date'])
                
                return df
                
        except Exception as e:
            self.logger.error(f"Error reading cached data: {e}")
            return pd.DataFrame()
    
    def _cache_data(self, df: pd.DataFrame):
        """Cache historical data to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Prepare data for insertion
                cache_df = df.copy()
                cache_df['timestamp'] = datetime.now().isoformat()
                
                # Insert or replace
                cache_df.to_sql('historical_data', conn, if_exists='append', 
                              index=False, method='ignore')
                
        except Exception as e:
            self.logger.error(f"Error caching data: {e}")
    
    def get_multiple_symbols_data(self, 
                                symbols: List[str],
                                interval: str = '1day',
                                days_back: int = 100,
                                exchange: str = "NSE") -> Dict[str, pd.DataFrame]:
        """
        Fetch historical data for multiple symbols
        
        Args:
            symbols: List of trading symbols
            interval: Data interval
            days_back: Number of days of historical data
            exchange: Exchange name
            
        Returns:
            Dictionary mapping symbols to their DataFrames
        """
        
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days_back)
        
        data = {}
        
        for symbol in symbols:
            token = self.get_instrument_token(symbol, exchange)
            if token:
                df = self.get_historical_data(
                    instrument_token=token,
                    interval=interval,
                    from_date=from_date,
                    to_date=to_date,
                    symbol=symbol
                )
                
                if not df.empty:
                    data[symbol] = df
                    self.logger.info(f"Loaded data for {symbol}: {len(df)} records")
                else:
                    self.logger.warning(f"No data found for {symbol}")
            else:
                self.logger.error(f"Could not find instrument token for {symbol}")
        
        return data
    
    def preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and preprocess OHLCV data
        
        Args:
            df: Raw OHLCV DataFrame
            
        Returns:
            Cleaned DataFrame
        """
        if df.empty:
            return df
        
        # Make a copy
        clean_df = df.copy()
        
        # Ensure date column is datetime
        if 'date' in clean_df.columns:
            clean_df['date'] = pd.to_datetime(clean_df['date'])
            clean_df.set_index('date', inplace=True)
        
        # Remove any duplicate timestamps
        clean_df = clean_df[~clean_df.index.duplicated(keep='first')]
        
        # Sort by date
        clean_df.sort_index(inplace=True)
        
        # Forward fill any missing values
        clean_df.fillna(method='ffill', inplace=True)
        
        # Remove any remaining NaN values
        clean_df.dropna(inplace=True)
        
        # Ensure positive values for OHLCV
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if col in clean_df.columns:
                clean_df[col] = clean_df[col].abs()
        
        return clean_df
    
    def get_latest_price(self, instrument_token: int) -> float:
        """
        Get latest price for an instrument
        
        Args:
            instrument_token: Zerodha instrument token
            
        Returns:
            Latest price or 0.0 if error
        """
        try:
            quote = self.kite.quote([instrument_token])
            if quote and str(instrument_token) in quote:
                return quote[str(instrument_token)]['last_price']
        except Exception as e:
            self.logger.error(f"Error fetching latest price: {e}")
        
        return 0.0
    
    def get_ohlc_data(self, symbols: List[str], exchange: str = "NSE") -> Dict[str, Dict]:
        """
        Get OHLC data for multiple symbols
        
        Args:
            symbols: List of trading symbols
            exchange: Exchange name
            
        Returns:
            Dictionary with OHLC data for each symbol
        """
        tokens = []
        symbol_token_map = {}
        
        for symbol in symbols:
            token = self.get_instrument_token(symbol, exchange)
            if token:
                tokens.append(token)
                symbol_token_map[str(token)] = symbol
        
        try:
            ohlc_data = self.kite.ohlc(tokens)
            result = {}
            
            for token_str, data in ohlc_data.items():
                symbol = symbol_token_map.get(token_str)
                if symbol:
                    result[symbol] = data
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error fetching OHLC data: {e}")
            return {}