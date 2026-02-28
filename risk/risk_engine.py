# risk/risk_engine.py

from domain.risk.risk_factory import build_risk_stack
from domain.risk.risk_config import RiskConfig
from domain.risk.risk_decision import RiskDecision
from domain.risk.risk_context import RiskContext


__all__ = [
    "RiskEngine",
    "RiskDecision",
    "RiskContext",
]


# ---- backward compatibility ----
def _deny(reason, rule=None):
    return RiskDecision.reject(reason)


if not hasattr(RiskDecision, "deny"):
    RiskDecision.deny = _deny


class RiskEngine:
    """
    Backward-compatible façade over RiskStack.

    evaluate(signal, context) -> signal | None
    """

    def __init__(
        self,
        position_manager=None,
        portfolio_manager=None,
        *,
        max_daily_loss_pct=None,
        max_drawdown_pct=None,
        correlation_matrix=None,
        **kwargs,
    ):

        config = RiskConfig()

        if max_daily_loss_pct is not None:
            config.daily_loss_limit = max_daily_loss_pct

        if max_drawdown_pct is not None:
            config.max_drawdown = max_drawdown_pct

        if correlation_matrix is not None:
            config.correlation_matrix = correlation_matrix

        self.stack = build_risk_stack(config)
        self.last_decision: RiskDecision | None = None
        self.is_frozen: bool = False

        # сохраняем лимиты локально для явного freeze
        self._daily_limit = max_daily_loss_pct
        self._dd_limit = max_drawdown_pct

    # ------------------------------------------------

    def evaluate(self, signal=None, context=None):

        if context is None:
            return None

        # если уже заморожены — блок
        if self.is_frozen:
            return None

        decision = self.stack.evaluate(context)
        self.last_decision = decision

        # ---- explicit freeze logic for legacy tests ----

        # 1. Daily loss freeze
        if (
            self._daily_limit is not None
            and hasattr(context, "daily_realized_pnl")
            and hasattr(context, "portfolio_value")
        ):
            equity = float(context.portfolio_value or 0.0)
            if equity > 0:
                daily_dd = float(context.daily_realized_pnl or 0.0) / equity
                if daily_dd <= -abs(self._daily_limit):
                    self.is_frozen = True
                    return None

        # 2. Max drawdown freeze
        if (
            self._dd_limit is not None
            and hasattr(context, "realized_pnl")
            and hasattr(context, "portfolio_value")
        ):
            equity = float(context.portfolio_value or 0.0)
            if equity > 0:
                dd = float(context.realized_pnl or 0.0) / equity
                if dd <= -abs(self._dd_limit):
                    self.is_frozen = True
                    return None

        # 3. Stack decision
        if not decision.allowed:
            return None

        return signal

    # ------------------------------------------------

    def validate(self, fill):
        return True

    # ------------------------------------------------

    def get_state(self):
        return self.stack.get_state()

    def load_state(self, state):
        self.stack.load_state(state)