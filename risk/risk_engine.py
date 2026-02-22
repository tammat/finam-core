import numpy as np

class RiskEngine:

    def __init__(
        self,
        max_position_pct=0.2,
        max_gross_exposure_pct=0.5,
        max_drawdown_pct=-0.2,
        correlation_matrix=None,
    ):
        self.max_position_pct = max_position_pct
        self.max_gross_exposure_pct = max_gross_exposure_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.correlation_matrix = correlation_matrix or {}

    def evaluate(self, signal, context):

        # 1️⃣ Position size limit
        notional = signal.qty * signal.price
        if notional > context.equity * self.max_position_pct:
            return None

        # 2️⃣ Gross exposure limit
        if context.gross_exposure + notional > context.equity * self.max_gross_exposure_pct:
            return None

        # 3️⃣ Cash check
        if signal.side == "BUY" and notional > context.cash:
            return None

        # 4️⃣ Correlation check
        correlated = self.correlation_matrix.get(signal.symbol, {})
        for symbol, corr in correlated.items():
            if abs(corr) > 0.8:
                # simple rule: block if already high exposure
                if context.gross_exposure > context.equity * 0.3:
                    return None

        return signal

    def evaluate(self, *args):

        # SIM mode: evaluate(state)
        if len(args) == 1:
            return args[0]

        # Standard mode: evaluate(signal, context)
        signal, context = args

        notional = signal.qty * signal.price

        if hasattr(context, "equity"):
            if hasattr(self, "max_position_pct"):
                if notional > context.equity * self.max_position_pct:
                    return None

        if hasattr(self, "correlation_matrix"):
            if signal.symbol in self.correlation_matrix:
                if context.gross_exposure > 0:
                    return None

        return signal