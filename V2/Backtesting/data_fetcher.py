from datetime import datetime, timedelta
from typing import Dict, List
import pandas as pd
from kiteconnect import KiteConnect
import logging

logger = logging.getLogger(__name__)

class HistoricalDataFetcher:
    
    INTERVALS = {
        '1min': 'minute',
        '5min': '5minute',
        '15min': '15minute',
        '1hour': '60minute',
        '1day': 'day'
    }
    
    def __init__(self, kite: KiteConnect):
        self.kite = kite
    
    def get_instrument_token(self, symbol: str, exchange: str = "NSE") -> int:
        instruments = self.kite.instruments(exchange)
        for inst in instruments:
            if inst['tradingsymbol'] == symbol and inst['exchange'] == exchange:
                return inst['instrument_token']
        raise ValueError(f"Symbol {symbol} not found on {exchange}")
    
    def fetch_historical_data(self, symbol: str, start_date: datetime, 
                             end_date: datetime, interval: str = "1day",
                             exchange: str = "NSE") -> pd.DataFrame:
        try:
            token = self.get_instrument_token(symbol, exchange)
            
            records = self.kite.historical_data(
                instrument_token=token,
                from_date=start_date,
                to_date=end_date,
                interval=self.INTERVALS.get(interval, interval)
            )
            
            if not records:
                logger.warning(f"No data for {symbol}")
                return pd.DataFrame()
            
            df = pd.DataFrame(records)
            df['symbol'] = symbol
            
            if 'date' in df.columns:
                df.rename(columns={'date': 'timestamp'}, inplace=True)
            
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()
    
    def fetch_multiple_symbols(self, symbols: List[str], start_date: datetime,
                               end_date: datetime, interval: str = "1day",
                               exchange: str = "NSE") -> Dict[str, pd.DataFrame]:
        data = {}
        for symbol in symbols:
            df = self.fetch_historical_data(symbol, start_date, end_date, 
                                           interval, exchange)
            if not df.empty:
                data[symbol] = df
                logger.info(f"Fetched {len(df)} records for {symbol}")
        return data

