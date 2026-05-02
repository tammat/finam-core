# risk/risk_engine.py

from finam_core.domain.risk.risk_factory import build_risk_stack
from finam_core.domain.risk.risk_config import RiskConfig
from finam_core.domain.risk.risk_decision import RiskDecision
from finam_core.domain.risk.risk_context import RiskContext

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

    evaluate(signal, context) -> RiskDecision
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

        self._daily_limit = max_daily_loss_pct
        self._dd_limit = max_drawdown_pct

    # ------------------------------------------------

    def evaluate(self, signal=None, context=None):
        # HARD GUARD
        if context is None:
            decision = RiskDecision.reject("no_context")
            self.last_decision = decision
            return decision

        # FROZEN
        if self.is_frozen:
            decision = RiskDecision.reject("frozen")
            self.last_decision = decision
            return decision

        # STACK
        decision = self.stack.evaluate(context)
        self.last_decision = decision

        # DAILY LOSS
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
                    decision = RiskDecision.reject("daily_loss_freeze")
                    self.last_decision = decision
                    return decision

        # DRAWDOWN
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
                    decision = RiskDecision.reject("max_drawdown_freeze")
                    self.last_decision = decision
                    return decision

        if decision is None:
            decision = RiskDecision.reject("no_decision")

        self.last_decision = decision
        return decision

    # ------------------------------------------------

    def validate(self, fill):
        return True

    def get_state(self):
        return self.stack.get_state()

    def load_state(self, state):
        self.stack.load_state(state)