from kiteconnect import KiteTicker
from typing import List, Callable, Dict
import logging

logger = logging.getLogger(__name__)

class DataStream:
    
    def __init__(self, api_key: str, access_token: str):
        self.api_key = api_key
        self.access_token = access_token
        self.kws = KiteTicker(api_key, access_token)
        self.callbacks: List[Callable] = []
        self.instrument_tokens: List[int] = []
    
    def add_callback(self, callback: Callable):
        self.callbacks.append(callback)
    
    def subscribe(self, instrument_tokens: List[int]):
        self.instrument_tokens = instrument_tokens
    
    def on_ticks(self, ws, ticks):
        for tick in ticks:
            for callback in self.callbacks:
                try:
                    callback(tick)
                except Exception as e:
                    logger.error(f"Callback error: {e}")
    
    def on_connect(self, ws, response):
        logger.info("WebSocket connected")
        ws.subscribe(self.instrument_tokens)
        ws.set_mode(ws.MODE_FULL, self.instrument_tokens)
    
    def on_close(self, ws, code, reason):
        logger.warning(f"WebSocket closed: {code} - {reason}")
    
    def on_error(self, ws, code, reason):
        logger.error(f"WebSocket error: {code} - {reason}")
    
    def start(self):
        self.kws.on_ticks = self.on_ticks
        self.kws.on_connect = self.on_connect
        self.kws.on_close = self.on_close
        self.kws.on_error = self.on_error
        
        logger.info("Starting data stream...")
        self.kws.connect(threaded=True)
    
    def stop(self):
        logger.info("Stopping data stream...")
        self.kws.close()

