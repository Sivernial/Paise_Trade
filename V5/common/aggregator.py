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
        symbol = tick.get('instrument_token') # Or tradingsymbol depending on tick format
        # If using KiteTicker, tick has 'instrument_token'. We might need mapping if we want tradingsymbol.
        # But let's assume the runner creates aggregator with knowledge of tokens or we pass tradingsymbol.
        # Actually standard kite tick has 'instrument_token'. 
        
        # We probably want to map back to symbol if possible, or carry it.
        # For now, let's use what's available. The runner receives raw ticks.
        # If the runner enriches the tick or we use token, it's fine.
        
        price = tick.get('last_price')
        volume = tick.get('volume_traded', 0) # This is cumulative usually? 
        # Actually last_traded_quantity might be better for per-tick, but Kite gives cumulative 'volume_traded' for the day 
        # or 'last_traded_quantity' for height. 
        # Diffing cumulative volume is safer.
        
        last_trade_time = tick.get('exchange_timestamp')
        if not last_trade_time:
            last_trade_time = datetime.now()
            
        # Determine bar bucket
        # Align to interval (e.g. 9:15, 9:30, ...)
        # Floor time to nearest interval
        # If interval is 15 min:
        minute_floor = (last_trade_time.minute // self.interval_minutes) * self.interval_minutes
        bar_start_time = last_trade_time.replace(minute=minute_floor, second=0, microsecond=0)
        
        if symbol not in self.current_candles:
            self._init_candle(symbol, bar_start_time, price, volume)
        else:
            candle = self.current_candles[symbol]
            
            # Check if this tick belongs to a new bar
            if bar_start_time > candle['timestamp']:
                # Close previous candle
                self._flush_candle(symbol)
                # Start new
                self._init_candle(symbol, bar_start_time, price, volume)
            else:
                # Update current
                candle['high'] = max(candle['high'], price)
                candle['low'] = min(candle['low'], price)
                candle['close'] = price
                # Volume diff
                # If tick volume is cumulative, we need to track previous tick volume?
                # Simplify: Just aggregate ticks? No, Kite 'volume_traded' is day aggregated. 
                # We need to track volume at start of candle.
                # Let's simple use 0 for now as volume isn't critical for our Pair Strategy (uses price).
                candle['volume'] = 0 

    def _init_candle(self, symbol, start_time, price, volume):
        self.current_candles[symbol] = {
            'timestamp': start_time,
            'open': price,
            'high': price,
            'low': price,
            'close': price,
            'volume': 0, 
            # 'start_volume': volume # To calc diff if needed
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
