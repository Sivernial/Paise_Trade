from datetime import datetime, timedelta
import pandas as pd
from typing import Dict, List, Callable, Optional
import logging

logger = logging.getLogger(__name__)

class TickAggregator:
    """
    Aggregates real-time ticks into OHLCV candles.
    """
    def __init__(self, interval_minutes: int = 15):
        self.interval_minutes = interval_minutes
        self.interval_delta = timedelta(minutes=interval_minutes)
        self.current_candles: Dict[str, Dict] = {} # symbol -> partial candle
        self.callbacks: List[Callable[[str, pd.DataFrame], None]] = []
        self.last_flush_time: Optional[datetime] = None

    def add_callback(self, callback: Callable):
        """
        Callback signature: (symbol: str, candle: pd.DataFrame)
        """
        self.callbacks.append(callback)

    def on_tick(self, ticks: List[Dict]):
        for tick in ticks:
            self._process_tick(tick)

    def _process_tick(self, tick: Dict):
        symbol = tick.get('instrument_token')
        price = tick.get('last_price')
        volume = tick.get('volume_traded', 0)
        
        last_trade_time = tick.get('exchange_timestamp')
        if not last_trade_time:
            last_trade_time = datetime.now()
            
        minute_floor = (last_trade_time.minute // self.interval_minutes) * self.interval_minutes
        bar_start_time = last_trade_time.replace(minute=minute_floor, second=0, microsecond=0)
        
        if symbol not in self.current_candles:
            self._init_candle(symbol, bar_start_time, price, volume)
        else:
            candle = self.current_candles[symbol]
            
            if bar_start_time > candle['timestamp']:
                self._flush_candle(symbol)
                self._init_candle(symbol, bar_start_time, price, volume)
            else:
                candle['high'] = max(candle['high'], price)
                candle['low'] = min(candle['low'], price)
                candle['close'] = price
                # Day's cumulative volume - volume at bar start
                candle['volume'] = volume - candle['start_volume']

    def _init_candle(self, symbol, start_time, price, volume):
        self.current_candles[symbol] = {
            'timestamp': start_time,
            'open': price,
            'high': price,
            'low': price,
            'close': price,
            'volume': 0,
            'start_volume': volume 
        }

    def _flush_candle(self, symbol):
        if symbol not in self.current_candles:
            return
            
        c = self.current_candles[symbol]
        
        # Create DataFrame for formatted candle
        df = pd.DataFrame([{
            'timestamp': c['timestamp'],
            'open': c['open'],
            'high': c['high'],
            'low': c['low'],
            'close': c['close'],
            'volume': c['volume']
        }])
        df.set_index('timestamp', inplace=True)
        
        # Trigger callbacks
        for cb in self.callbacks:
            try:
                cb(symbol, df)
            except Exception as e:
                logger.error(f"Error in aggregator callback: {e}")
        
        # Remove from current (will be re-inited on next tick)
        del self.current_candles[symbol]
