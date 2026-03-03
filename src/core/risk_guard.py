class RiskGuard:

    def __init__(self, max_position=100):
        self.max_position = max_position

    def allow(self, current_qty, signal_side, signal_qty):
        if signal_side == "BUY":
            return current_qty + signal_qty <= self.max_position
        if signal_side == "SELL":
            return current_qty - signal_qty >= -self.max_position
        return False