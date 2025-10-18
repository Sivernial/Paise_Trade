from kiteconnect import KiteTicker
import threading

class LiveDataStreamer:
    def __init__(self, api_key, access_token, instrument_tokens, strategy_callback):
        self.kws = KiteTicker(api_key, access_token)
        self.instrument_tokens = instrument_tokens
        self.strategy_callback = strategy_callback

    def on_ticks(self, ws, ticks):
        # Send ticks to strategy logic
        for tick in ticks:
            self.strategy_callback(tick)

    def on_connect(self, ws, response):
        ws.subscribe(self.instrument_tokens)
        ws.set_mode(ws.MODE_FULL, self.instrument_tokens)
        print(f"✅ Subscribed to tokens: {self.instrument_tokens}")

    def on_close(self, ws, code, reason):
        print(f"⚠️ Connection closed: {code} - {reason}")

    def start(self):
        self.kws.on_ticks = self.on_ticks
        self.kws.on_connect = self.on_connect
        self.kws.on_close = self.on_close
        print("🚀 Starting live data stream...")
        self.kws.connect(threaded=True)
