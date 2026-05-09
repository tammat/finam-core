# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioRiskDecision:
    allowed: bool
    reason: str
    portfolio_heat: float
    symbol_heat: float
    margin_utilization: float
    daily_loss_pct: float
    drawdown_pct: float


class PortfolioRiskGate:
    """Русский комментарий: централизованный portfolio-level risk gate."""

    def evaluate(
        self,
        *,
        equity: float,
        total_exposure: float,
        symbol_exposure: float,
        used_margin: float,
        daily_pnl: float,
        peak_equity: float,
        current_equity: float,
        max_portfolio_heat: float = 0.30,
        max_symbol_heat: float = 0.10,
        max_margin_utilization: float = 0.65,
        max_daily_loss_pct: float = 0.02,
        max_drawdown_pct: float = 0.03,
    ) -> PortfolioRiskDecision:
        if equity <= 0:
            return PortfolioRiskDecision(False, "invalid_equity", 0.0, 0.0, 0.0, 0.0, 0.0)

        portfolio_heat = total_exposure / equity
        symbol_heat = symbol_exposure / equity
        margin_utilization = used_margin / equity
        daily_loss_pct = abs(min(daily_pnl, 0.0)) / equity
        drawdown_pct = abs(min((current_equity - peak_equity) / peak_equity, 0.0)) if peak_equity > 0 else 0.0

        if portfolio_heat > max_portfolio_heat:
            reason = "portfolio_heat"
        elif symbol_heat > max_symbol_heat:
            reason = "symbol_heat"
        elif margin_utilization > max_margin_utilization:
            reason = "margin_utilization"
        elif daily_loss_pct > max_daily_loss_pct:
            reason = "daily_loss"
        elif drawdown_pct > max_drawdown_pct:
            reason = "drawdown"
        else:
            reason = "ok"

        return PortfolioRiskDecision(
            allowed=reason == "ok",
            reason=reason,
            portfolio_heat=round(portfolio_heat, 6),
            symbol_heat=round(symbol_heat, 6),
            margin_utilization=round(margin_utilization, 6),
            daily_loss_pct=round(daily_loss_pct, 6),
            drawdown_pct=round(drawdown_pct, 6),
        )
