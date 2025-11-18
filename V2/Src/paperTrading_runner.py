import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime
import logging
import time
from PaperTrader import PaperTrader
from Algorithms import MACrossoverStrategy
from DataStream_Engine import DataStream
from login import get_kite_instance

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_paper_trading():
    logger.info("Starting paper trading...")
    
    kite = get_kite_instance()
    if not kite:
        logger.error("Failed to initialize Kite")
        return
    
    strategy = MACrossoverStrategy({'fast_period': 10, 'slow_period': 20})
    trader = PaperTrader(strategy, initial_capital=100000)
    
    api_key = os.getenv("API_KEY")
    access_token_file = "access_token.txt"
    
    if not os.path.exists(access_token_file):
        logger.error("Access token not found. Please login first.")
        return
    
    with open(access_token_file, 'r') as f:
        access_token = f.read().strip()
    
    symbols = ['RELIANCE', 'TCS', 'INFY']
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
    
    logger.info("Paper trading started. Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(60)
            status = trader.get_status()
            logger.info(f"Portfolio Value: ${status['total_value']:,.2f} | Returns: {status['returns']:.2%}")
    
    except KeyboardInterrupt:
        logger.info("Stopping paper trading...")
        stream.stop()
        final_status = trader.get_status()
        logger.info(f"Final Value: ${final_status['total_value']:,.2f}")
        logger.info(f"Total Returns: {final_status['returns']:.2%}")

if __name__ == "__main__":
    run_paper_trading()

