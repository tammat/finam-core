# risk/risk_engine.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

class RiskDecision:
    def __init__(self, approved: bool, reason: str | None = None):
        self.approved = approved
        self.reason = reason

class RiskEngine:
    """
    Runtime / post-signal risk gate.
    Expected contract by tests:
      - risk.evaluate(signal, context) -> signal (truthy) if approved, else None
      - maintains freeze-state on daily-loss/max-DD triggers
    """

    def __init__(
        self,
        position_manager: Any = None,
        portfolio_manager: Any = None,
        *,
        max_daily_loss_pct: float | None = None,
        max_drawdown_pct: float | None = None,
        max_position_pct: float | None = None,
        max_gross_exposure_pct: float | None = None,
        max_portfolio_heat: float | None = None,
        correlation_matrix: dict[str, dict[str, float]] | None = None,
        correlation_threshold: float = 0.8,
        rules: list[Any] | None = None,
    ):
        self.position_manager = position_manager
        self.portfolio_manager = portfolio_manager

        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.max_position_pct = max_position_pct
        self.max_gross_exposure_pct = max_gross_exposure_pct
        self.max_portfolio_heat = max_portfolio_heat
        self.correlation_matrix = correlation_matrix or {}
        self.correlation_threshold = correlation_threshold

        self.rules = rules or []

        # freeze-state
        self.is_frozen: bool = False
        self.freeze_date = None

        # adaptive scaling / internal HWM
        self.base_risk_multiplier = 1.0
        self.current_risk_multiplier = 1.0
        self.equity_high_watermark: float | None = None
        self.last_reject_reason: str | None = None

    def evaluate(self, signal: Any = None, context: Any = None):
        self.last_reject_reason = None
        self._daily_reset()
        self._update_drawdown(context)

        if self._check_freeze():
            self.last_reject_reason = "ENGINE_FROZEN"
            return None

        if self._check_daily_loss(context):
            self.last_reject_reason = "DAILY_LOSS_LIMIT"
            return None

        if self._check_global_drawdown(context):
            self.last_reject_reason = "MAX_DRAWDOWN_LIMIT"
            return None

        if self._check_custom_rules(signal, context):
            self.last_reject_reason = "CUSTOM_RULE_REJECT"
            return None
        if signal is None or context is None:
            return signal

        if self._check_position_limit(signal, context):
            self.last_reject_reason = "POSITION_LIMIT"
            return None
        if self._check_gross_exposure(signal, context):
            self.last_reject_reason = "GROSS_EXPOSURE_LIMIT"
            return None

        if self._check_portfolio_heat(signal, context):
            self.last_reject_reason = "PORTFOLIO_HEAT_LIMIT"
            return None

        if self._check_correlation(signal, context):
            self.last_reject_reason = "CORRELATION_BLOCK"
            return None

        return signal

    def _daily_reset(self):
        from datetime import datetime, UTC
        today = datetime.now(UTC).date()
        self.freeze_date = None
        return today

    def _update_drawdown(self, context):
        if context is None or not hasattr(context, "equity"):
            return

        equity = float(getattr(context, "equity") or 0.0)

        if self.equity_high_watermark is None:
            realized = float(getattr(context, "realized_pnl", 0.0) or 0.0)
            unrealized = float(getattr(context, "unrealized_pnl", 0.0) or 0.0)
            reconstructed_peak = equity - realized - unrealized
            self.equity_high_watermark = max(equity, reconstructed_peak)

        if equity > (self.equity_high_watermark or 0.0):
            self.equity_high_watermark = equity

        if self.equity_high_watermark:
            self.current_drawdown = (equity - self.equity_high_watermark) / self.equity_high_watermark
        else:
            self.current_drawdown = 0.0

    def _check_freeze(self):
        return self.is_frozen

    def _check_daily_loss(self, context):
        if self.max_daily_loss_pct is None or context is None:
            return False

        daily_dd = getattr(context, "daily_drawdown", None)

        if daily_dd is None and hasattr(context, "daily_realized_pnl") and hasattr(context, "equity"):
            eq = float(getattr(context, "equity") or 0.0)
            if eq > 0:
                daily_dd = float(getattr(context, "daily_realized_pnl") or 0.0) / eq

        if daily_dd is not None and float(daily_dd) <= -abs(self.max_daily_loss_pct):
            from datetime import datetime, UTC
            self.is_frozen = True
            self.freeze_date = datetime.now(UTC).date()
            return True

        return False

    def _check_global_drawdown(self, context):
        if self.max_drawdown_pct is None or context is None:
            return False

        dd = float(self.current_drawdown or 0.0)
        abs_dd = abs(dd)

        if abs_dd >= 0.15:
            self.current_risk_multiplier = 0.0
        elif abs_dd >= 0.10:
            self.current_risk_multiplier = 0.4
        elif abs_dd >= 0.05:
            self.current_risk_multiplier = 0.7
        else:
            self.current_risk_multiplier = 1.0

        if dd <= -abs(self.max_drawdown_pct):
            from datetime import datetime, UTC
            self.is_frozen = True
            self.freeze_date = datetime.now(UTC).date()
            return True

        return False

    def _check_custom_rules(self, signal, context):
        for rule in self.rules:
            res = rule(signal=signal, context=context)
            if res is False:
                return True
        return False

    def _check_position_limit(self, signal, context):
        if self.max_position_pct is None:
            return False

        qty = abs(float(getattr(signal, "qty", 0) or 0.0))
        price = abs(float(getattr(signal, "price", 0) or 0.0))
        notional = (qty * price) * float(self.current_risk_multiplier or 1.0)

        equity = float(getattr(context, "equity", 0) or 0.0)
        if equity > 0 and (notional / equity) > float(self.max_position_pct):
            return True

        return False

    def _check_gross_exposure(self, signal, context):
        if self.max_gross_exposure_pct is None:
            return False

        current_exposure = float(getattr(context, "gross_exposure", 0) or 0.0)
        qty = abs(float(getattr(signal, "qty", 0) or 0.0))
        price = abs(float(getattr(signal, "price", 0) or 0.0))
        new_notional = qty * price

        equity = float(getattr(context, "equity", 0) or 0.0)
        if equity > 0 and ((current_exposure + new_notional) / equity) > float(self.max_gross_exposure_pct):
            return True

        return False

    def _check_portfolio_heat(self, signal, context):
        if self.max_portfolio_heat is None:
            return False

        current_heat = float(getattr(context, "portfolio_heat", 0) or 0.0)
        atr = getattr(signal, "atr", None)

        qty = abs(float(getattr(signal, "qty", 0) or 0.0))
        price = abs(float(getattr(signal, "price", 0) or 0.0))
        additional_heat = qty * (abs(float(atr)) if atr is not None else price)

        if (current_heat + additional_heat) > float(self.max_portfolio_heat):
            return True

        return False

    def _check_correlation(self, signal, context):
        if not self.correlation_matrix:
            return False

        correlated = self.correlation_matrix.get(getattr(signal, "symbol", None), {})
        positions = getattr(context, "positions", {}) or {}

        for sym, corr in correlated.items():
            pos = positions.get(sym)
            if pos is None:
                continue
            pos_qty = float(getattr(pos, "qty", 0) or 0.0)
            if abs(pos_qty) > 0 and abs(float(corr)) >= float(self.correlation_threshold):                return True

        return False