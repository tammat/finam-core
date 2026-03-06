import os
import inspect
from finam_core.domain.risk.risk_decision import RiskDecision


class ExposureRule:
    """
    Limits interpretation (compat):
      - if 0 < limit <= 1 : fraction of equity
      - if limit > 1      : treat as PERCENT (e.g. 150.0 => 150%) if limit > 1.0 and <= 1000
                            (so 150 => 1.5, 20 => 0.2)
                            if you REALLY need absolute RUB, pass very large values (e.g. > 10_000)
    Context must provide:
      - equity (preferred) OR starting_capital (fallback)
      - total_exposure
      - current_symbol_exposure
      - trade_value
    """

    def __init__(self, max_total_exposure: float, max_symbol_exposure: float):
        self.max_total_exposure = float(max_total_exposure)
        self.max_symbol_exposure = float(max_symbol_exposure)

    @staticmethod
    def _resolve_pct(limit: float) -> float:
        """
        Normalize env/config values to a fraction.
        - 1.5 means 150%
        - 150.0 means 150% (will be normalized to 1.5)
        - 0.2 means 20%
        """
        lim = float(limit or 0.0)
        if lim <= 0:
            return 0.0
        # common "PCT" style: 150.0, 20.0, 3.0 etc.
        if lim > 1.0 and lim <= 1000.0:
            return lim / 100.0
        return lim  # already fraction

    def evaluate(self, context):
        # Prefer equity; fallback to starting_capital (legacy)
        equity = getattr(context, "equity", None)
        if equity is None:
            equity = getattr(context, "portfolio_value", None)
        if equity is None:
            equity = getattr(context, "starting_capital", 0.0)

        try:
            equity = float(equity or 0.0)
        except Exception:
            equity = 0.0

        # safe default: if equity <= 0 -> forbid increasing exposure
        if equity <= 0:
            return RiskDecision.reject("equity_non_positive")

        total_exposure = float(getattr(context, "total_exposure", 0.0) or 0.0)
        sym_exposure = float(getattr(context, "current_symbol_exposure", 0.0) or 0.0)
        trade_value = float(getattr(context, "trade_value", 0.0) or 0.0)

        max_total_pct = self._resolve_pct(self.max_total_exposure)
        max_symbol_pct = self._resolve_pct(self.max_symbol_exposure)

        max_total = equity * max_total_pct if max_total_pct > 0 else 0.0
        max_symbol = equity * max_symbol_pct if max_symbol_pct > 0 else 0.0

        new_total = total_exposure + trade_value
        new_symbol = sym_exposure + trade_value

        if os.getenv("RISK_DEBUG") == "1":
            print(
                "RISK_DEBUG ExposureRule "
                f"file={inspect.getfile(self.__class__)} "
                f"equity={equity:.2f} total_exposure={total_exposure:.2f} "
                f"sym_exposure={sym_exposure:.2f} trade_value={trade_value:.2f} "
                f"max_total_raw={self.max_total_exposure} max_symbol_raw={self.max_symbol_exposure} "
                f"max_total_pct={max_total_pct:.6f} max_symbol_pct={max_symbol_pct:.6f} "
                f"max_total={max_total:.2f} max_symbol={max_symbol:.2f} "
                f"new_total={new_total:.2f} new_symbol={new_symbol:.2f}",
                flush=True,
            )

        if max_total > 0.0 and new_total > max_total:
            return RiskDecision.reject("max_total_exposure_exceeded")

        if max_symbol > 0.0 and new_symbol > max_symbol:
            return RiskDecision.reject("max_symbol_exposure_exceeded")

        return RiskDecision.allow()
