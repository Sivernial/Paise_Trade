import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime
import logging
import time
from LiveTrader import LiveTrader
from Algorithms import MACrossoverStrategy
from DataStream_Engine import DataStream
from login import get_kite_instance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_live_trading():
    logger.info("=" * 60)
    logger.info("WARNING: LIVE TRADING MODE")
    logger.info("This will execute REAL trades with REAL money!")
    logger.info("=" * 60)
    
    confirmation = input("Type 'YES' to confirm live trading: ")
    if confirmation != "YES":
        logger.info("Live trading cancelled")
        return
    
    kite = get_kite_instance()
    if not kite:
        logger.error("Failed to initialize Kite")
        return
    
    strategy = MACrossoverStrategy({'fast_period': 10, 'slow_period': 20})
    trader = LiveTrader(kite, strategy)
    
    api_key = os.getenv("API_KEY")
    access_token_file = "access_token.txt"
    
    if not os.path.exists(access_token_file):
        logger.error("Access token not found. Please login first.")
        return
    
    with open(access_token_file, 'r') as f:
        access_token = f.read().strip()
    
    symbols = ['RELIANCE', 'TCS']
    instrument_tokens = []
    
    try:
        instruments = kite.instruments("NSE")
        for inst in instruments:
            if inst['tradingsymbol'] in symbols:
                instrument_tokens.append(inst['instrument_token'])
    except Exception as e:
        logger.error(f"Error fetching instruments: {e}")
        return
    
    stream = DataStream(api_key, access_token)
    stream.subscribe(instrument_tokens)
    stream.add_callback(trader.on_tick)
    
    stream.start()
    
    logger.info("Live trading started. Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(60)
            status = trader.get_status()
            logger.info(f"Active Positions: {status['positions']}")
    
    except KeyboardInterrupt:
        logger.info("Stopping live trading...")
        stream.stop()
        logger.info("Live trading stopped")

if __name__ == "__main__":
    run_live_trading()

