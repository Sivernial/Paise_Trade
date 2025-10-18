import os
from dotenv import load_dotenv
from kiteconnect import KiteConnect
from core.data_stream import LiveDataStreamer
from core.strategy import BaseStrategy
from core.trader import Trader

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
with open("access_token.txt") as f:
    ACCESS_TOKEN = f.read().strip()

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

# Example instrument (Reliance token ID = 738561)
instrument_tokens = [738561]

class DemoStrategy(BaseStrategy):
    def __init__(self, kite):
        super().__init__(kite)
        self.trader = Trader(kite)

    def on_tick(self, tick):
        token = tick['instrument_token']
        ltp = tick['last_price']
        print(f"Tick | Token: {token} | LTP: {ltp}")

        # Example: Trigger buy if LTP < 2500
        if ltp < 2500:
            self.trader.buy("RELIANCE", 1, ltp)
        elif ltp > 2600:
            self.trader.sell("RELIANCE", 1, ltp)

def strategy_callback(tick):
    strategy.on_tick(tick)

strategy = DemoStrategy(kite)
streamer = LiveDataStreamer(API_KEY, ACCESS_TOKEN, instrument_tokens, strategy_callback)

if __name__ == "__main__":
    streamer.start()

    # 🕒 Keep the script running
    while True:
        try:
            pass  # keep alive
        except KeyboardInterrupt:
            print("\n🛑 Exiting...")
            break
