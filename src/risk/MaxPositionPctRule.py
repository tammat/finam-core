class MaxPositionPctRule:
    def __init__(self, max_pct):
        self.max_pct = max_pct

    def evaluate(self, signal, context):
        notional = signal.qty * signal.price
        if notional > context.equity * self.max_pct:
            return None
        return signal