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


def _deny(reason, rule=None):
    return RiskDecision.reject(reason)


if not hasattr(RiskDecision, "deny"):
    RiskDecision.deny = _deny


class RiskEngine:
    """
    RiskEngine facade over RiskStack.

    pipeline:

        signal
           ↓
        evaluate(signal, context)
           ↓
        signal | None
    """

    def __init__(
        self,
        position_manager=None,
        portfolio_manager=None,
        *,
        max_daily_loss_pct=None,
        max_drawdown_pct=None,
        correlation_matrix=None,
        self.last_decision = None
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

    def evaluate(self, signal=None, context: RiskContext | None = None):
        decision = self.stack.evaluate(context)
        self.last_decision = decision

        for flag in ("allowed", "is_allowed", "ok", "pass_", "approved"):
            if hasattr(decision, flag):
                return bool(getattr(decision, flag))

        # если decision — bool (бывает)
        if isinstance(decision, bool):
            return decision

        # fallback: truthy
        return bool(decision)

        if signal is None:
            return None

        if context is None:
            return signal

        if self.is_frozen:
            return None

        decision = self.stack.evaluate(context)
        self.last_decision = decision

        equity = float(getattr(context, "portfolio_value", 0.0) or 0.0)

        # ---- daily loss check ----

        if (
            self._daily_limit is not None
            and equity > 0
            and hasattr(context, "daily_realized_pnl")
        ):

            daily_dd = float(context.daily_realized_pnl or 0.0) / equity

            if daily_dd <= -abs(self._daily_limit):
                self.is_frozen = True
                return None

        # ---- drawdown check ----

        if (
            self._dd_limit is not None
            and equity > 0
            and hasattr(context, "realized_pnl")
        ):

            dd = float(context.realized_pnl or 0.0) / equity

            if dd <= -abs(self._dd_limit):
                self.is_frozen = True
                return None

        # ---- stack decision ----

        if not decision.allowed:
            return None

        return signal

    # ------------------------------------------------

    def validate(self, fill):
        """
        validate executed trade (post-trade check)
        """
        return True

    # ------------------------------------------------

    def get_state(self):
        return self.stack.get_state()

    def load_state(self, state):
        self.stack.load_state(state)

    # ------------------------------------------------

    def reset_freeze(self):
        self.is_frozen = False