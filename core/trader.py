class Trader:
    def __init__(self, kite):
        self.kite = kite

    def buy(self, symbol, qty, price=None):
        print(f"🟢 BUY signal: {symbol} x {qty} @ {price}")
        # Example order placement (can be expanded)
        # self.kite.place_order(...)

    def sell(self, symbol, qty, price=None):
        print(f"🔴 SELL signal: {symbol} x {qty} @ {price}")
        # self.kite.place_order(...)
