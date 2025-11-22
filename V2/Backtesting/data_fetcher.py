from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
from kiteconnect import KiteConnect
import logging
from .config import MarketDataConfig

logger = logging.getLogger(__name__)

class HistoricalDataFetcher:
    
    INTERVALS = MarketDataConfig.INTERVALS
    
    def __init__(self, kite: KiteConnect):
        self.kite = kite
    
    @staticmethod
    def resample_ohlcv(df: pd.DataFrame, target_interval: str) -> pd.DataFrame:
        """
        Resample 1-min data to higher timeframe (e.g., 5min, 15min)
        Preserves OHLCV structure and maintains trading session logic
        """
        if df.empty:
            return df
        
        resampled = df.resample(target_interval, label='right', closed='right').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()
        
        if 'symbol' in df.columns:
            resampled['symbol'] = df['symbol'].iloc[0]
        
        return resampled
    
    def get_instrument_token(self, symbol: str, exchange: str = None) -> int:
        if exchange is None:
            exchange = MarketDataConfig.EXCHANGE
        
        # ✅ For index symbols, try multiple variations and exchanges
        if "NIFTY" in symbol.upper() or "SENSEX" in symbol.upper():
            # Try common index variations
            symbol_variations = [
                symbol,
                symbol.replace(" ", ""),  # "NIFTY 50" -> "NIFTY50"
                symbol.replace(" ", "_"),  # "NIFTY 50" -> "NIFTY_50"
                symbol.upper().replace(" ", ""),
            ]
            exchanges_to_try = [exchange, "NSE", "INDICES"]
            
            for exch in exchanges_to_try:
                try:
                    instruments = self.kite.instruments(exch)
                    for var in symbol_variations:
                        for inst in instruments:
                            if inst['tradingsymbol'] == var:
                                logger.info(f"✅ Found {symbol} as '{var}' on {exch} (token: {inst['instrument_token']})")
                                return inst['instrument_token']
                except Exception as e:
                    logger.debug(f"Could not fetch instruments from {exch}: {e}")
                    continue
        
        # Standard lookup for regular stocks
        instruments = self.kite.instruments(exchange)
        for inst in instruments:
            if inst['tradingsymbol'] == symbol and inst['exchange'] == exchange:
                return inst['instrument_token']
        
        raise ValueError(f"Symbol {symbol} not found on {exchange}. Try checking available instruments.")
    
    def fetch_historical_data(self, symbol: str, start_date: datetime, 
                             end_date: datetime, interval: str = None,
                             exchange: str = None) -> pd.DataFrame:
        if interval is None:
            interval = MarketDataConfig.INTERVAL
        if exchange is None:
            exchange = MarketDataConfig.EXCHANGE
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
                               end_date: datetime, interval: str = None,
                               exchange: str = None) -> Dict[str, pd.DataFrame]:
        data = {}
        for symbol in symbols:
            df = self.fetch_historical_data(symbol, start_date, end_date, 
                                           interval, exchange)
            if not df.empty:
                data[symbol] = df
                logger.info(f"Fetched {len(df)} records for {symbol}")
        return data
    
    def fetch_and_resample(self, symbols: List[str], start_date: datetime,
                          end_date: datetime, fetch_interval: str = '1min',
                          signal_interval: str = '5min',
                          exchange: str = None) -> tuple:
        raw_data = {}
        resampled_data = {}
        
        for symbol in symbols:
            df_raw = self.fetch_historical_data(symbol, start_date, end_date, 
                                               fetch_interval, exchange)
            if not df_raw.empty:
                raw_data[symbol] = df_raw
                
                if fetch_interval != signal_interval:
                    df_resampled = self.resample_ohlcv(df_raw, signal_interval)
                    resampled_data[symbol] = df_resampled
                    logger.info(f"Fetched {len(df_raw)} {fetch_interval} bars for {symbol}, "
                              f"resampled to {len(df_resampled)} {signal_interval} bars")
                else:
                    resampled_data[symbol] = df_raw
                    logger.info(f"Fetched {len(df_raw)} {fetch_interval} records for {symbol}")
        
        return raw_data, resampled_data

