class DrawdownRule:
    def __init__(self, max_drawdown):
        self.max_drawdown = max_drawdown

    def evaluate(self, signal, context):
        if context.drawdown < -self.max_drawdown:
            return None
        return signal