class BaseStrategy:
    def __init__(self, kite):
        self.kite = kite

    def on_tick(self, tick):
        """Called every time a new tick is received"""
        raise NotImplementedError("Implement in subclass")
