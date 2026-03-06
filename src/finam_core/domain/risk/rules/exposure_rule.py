from finam_core.domain.risk.risk_decision import RiskDecision
from finam_core.domain.risk.risk_context import RiskContext


class ExposureRule:

    def __init__(self, max_total_exposure: float, max_symbol_exposure: float):
        self.max_total_exposure = max_total_exposure
        self.max_symbol_exposure = max_symbol_exposure

    def evaluate(self, context):
        # Interpret limits as:
        # - absolute notional (RUB) if > 1
        # - fraction of starting_capital if 0 < limit <= 1
        starting_capital = getattr(context, "starting_capital", None)
        try:
            starting_capital = float(starting_capital) if starting_capital is not None else 0.0
        except Exception:
            starting_capital = 0.0

        def _resolve_limit(limit: float) -> float:
            try:
                lim = float(limit)
            except Exception:
                lim = 0.0
            if 0.0 < lim <= 1.0 and starting_capital > 0.0:
                return lim * starting_capital
            return lim

        max_total = _resolve_limit(self.max_total_exposure)
        max_symbol = _resolve_limit(self.max_symbol_exposure)

        new_total = float(getattr(context, "total_exposure", 0.0) or 0.0) + float(
            getattr(context, "trade_value", 0.0) or 0.0)
        if max_total > 0.0 and new_total > max_total:
            return (False, "max_total_exposure_exceeded")

        new_symbol = float(getattr(context, "current_symbol_exposure", 0.0) or 0.0) + float(
            getattr(context, "trade_value", 0.0) or 0.0)
        if max_symbol > 0.0 and new_symbol > max_symbol:
            return (False, "max_symbol_exposure_exceeded")

        return (True, None)