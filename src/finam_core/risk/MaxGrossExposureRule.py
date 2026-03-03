class MaxGrossExposureRule:
    def __init__(self, max_pct):
        self.max_pct = max_pct

    def evaluate(self, signal, context):
        new_exposure = context.gross_exposure + abs(signal.qty * signal.price)
        if new_exposure > context.equity * self.max_pct:
            return None
        return signal