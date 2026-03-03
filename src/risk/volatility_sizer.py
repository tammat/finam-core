from dataclasses import dataclass
from risk.context import RiskContext


@dataclass(frozen=True)
class VolatilitySizer:
    risk_pct: float
    atr_multiplier: float = 1.0
    enable_drawdown_scaling: bool = True

    def _drawdown_multiplier(self, context: RiskContext) -> float:
        if not self.enable_drawdown_scaling:
            return 1.0

        dd = abs(getattr(context, "drawdown", 0.0))

        if dd < 0.05:
            return 1.0
        elif dd < 0.10:
            return 0.5
        return 0.0

    def calculate(self, price: float, atr: float | None, context: RiskContext) -> float:
        if context.equity <= 0 or price <= 0:
            return 0.0

        multiplier = self._drawdown_multiplier(context)
        if multiplier == 0.0:
            return 0.0

        effective_risk = context.equity * self.risk_pct * multiplier

        stop_distance = atr * self.atr_multiplier if atr and atr > 0 else price
        if stop_distance <= 0:
            return 0.0

        return effective_risk / stop_distance