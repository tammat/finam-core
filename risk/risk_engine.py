# risk/risk_engine.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional


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

        self.rules = rules or []

        # freeze-state
        self.is_frozen: bool = False
        self.freeze_date = None

        # adaptive scaling / internal HWM
        self.base_risk_multiplier = 1.0
        self.current_risk_multiplier = 1.0
        self.equity_high_watermark: float | None = None
        self.current_drawdown: float = 0.0

    def evaluate(self, signal: Any = None, context: Any = None):
        # -------- daily reset --------
        from datetime import datetime, UTC
        today = datetime.now(UTC).date()
        #self.is_frozen = False
        self.freeze_date = None

        # -------- HWM drawdown tracking --------
        if context is not None and hasattr(context, "equity"):
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

        # -------- freeze guard --------
        if self.is_frozen:
            return None

        # -------- daily loss guard --------
        if self.max_daily_loss_pct is not None and context is not None:
            daily_dd = getattr(context, "daily_drawdown", None)
            # некоторые контексты дают daily_realized_pnl вместо daily_drawdown — поддержим
            if daily_dd is None and hasattr(context, "daily_realized_pnl") and hasattr(context, "equity"):
                eq = float(getattr(context, "equity") or 0.0)
                if eq > 0:
                    daily_dd = float(getattr(context, "daily_realized_pnl") or 0.0) / eq

            if daily_dd is not None and float(daily_dd) <= -abs(self.max_daily_loss_pct):
                self.is_frozen = True
                self.freeze_date = today
                return None

        # -------- global drawdown guard + adaptive scaling --------
        if self.max_drawdown_pct is not None and context is not None:
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
                self.is_frozen = True
                self.freeze_date = today
                return None

        # -------- custom rules --------
        for rule in self.rules:
            res = rule(signal=signal, context=context)
            if res is False:
                return None

        if signal is None or context is None:
            return signal

        # -------- position size limit --------
        if self.max_position_pct is not None:
            qty = abs(float(getattr(signal, "qty", 0) or 0.0))
            price = abs(float(getattr(signal, "price", 0) or 0.0))
            notional = (qty * price) * float(self.current_risk_multiplier or 1.0)

            equity = float(getattr(context, "equity", 0) or 0.0)
            if equity > 0 and (notional / equity) > float(self.max_position_pct):
                return None

        # -------- gross exposure limit --------
        if self.max_gross_exposure_pct is not None:
            current_exposure = float(getattr(context, "gross_exposure", 0) or 0.0)
            qty = abs(float(getattr(signal, "qty", 0) or 0.0))
            price = abs(float(getattr(signal, "price", 0) or 0.0))
            new_notional = qty * price

            equity = float(getattr(context, "equity", 0) or 0.0)
            if equity > 0 and ((current_exposure + new_notional) / equity) > float(self.max_gross_exposure_pct):
                return None

        # -------- portfolio heat limit --------
        if self.max_portfolio_heat is not None:
            current_heat = float(getattr(context, "portfolio_heat", 0) or 0.0)
            atr = getattr(signal, "atr", None)

            qty = abs(float(getattr(signal, "qty", 0) or 0.0))
            price = abs(float(getattr(signal, "price", 0) or 0.0))
            additional_heat = qty * (abs(float(atr)) if atr is not None else price)

            if (current_heat + additional_heat) > float(self.max_portfolio_heat):
                return None

        # -------- correlation block --------
        if self.correlation_matrix:
            correlated = self.correlation_matrix.get(getattr(signal, "symbol", None), {})
            positions = getattr(context, "positions", {}) or {}

            for sym, corr in correlated.items():
                pos = positions.get(sym)
                if pos is None:
                    continue
                pos_qty = float(getattr(pos, "qty", 0) or 0.0)
                if abs(pos_qty) > 0 and abs(float(corr)) >= 0.8:
                    return None

        return signal