# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DailyRiskState:
    start_equity: float
    current_equity: float
    peak_equity: float
    daily_pnl: float
    drawdown_abs: float
    drawdown_pct: float
    daily_loss_pct: float
    kill_switch: bool
    reason: str


class DailyRiskTracker:
    """
    Русский комментарий:
    Считает дневной риск по equity curve.
    Пока чистая логика без БД — чтобы безопасно вшить в RiskContext.
    """

    def calculate(
        self,
        *,
        equities: list[float],
        max_daily_loss_pct: float = 3.0,
        max_drawdown_pct: float = 10.0,
    ) -> DailyRiskState:
        clean = [float(x) for x in equities if x is not None]

        if not clean:
            return DailyRiskState(
                start_equity=0.0,
                current_equity=0.0,
                peak_equity=0.0,
                daily_pnl=0.0,
                drawdown_abs=0.0,
                drawdown_pct=0.0,
                daily_loss_pct=0.0,
                kill_switch=False,
                reason="no_equity_data",
            )

        start = clean[0]
        current = clean[-1]
        peak = max(clean)

        daily_pnl = current - start
        drawdown_abs = peak - current

        daily_loss_pct = abs(daily_pnl) / start * 100.0 if start > 0 and daily_pnl < 0 else 0.0
        drawdown_pct = drawdown_abs / peak * 100.0 if peak > 0 else 0.0

        kill = False
        reason = "ok"

        if daily_loss_pct >= float(max_daily_loss_pct):
            kill = True
            reason = "daily_loss_limit"

        if drawdown_pct >= float(max_drawdown_pct):
            kill = True
            reason = "drawdown_limit"

        return DailyRiskState(
            start_equity=round(start, 2),
            current_equity=round(current, 2),
            peak_equity=round(peak, 2),
            daily_pnl=round(daily_pnl, 2),
            drawdown_abs=round(drawdown_abs, 2),
            drawdown_pct=round(drawdown_pct, 2),
            daily_loss_pct=round(daily_loss_pct, 2),
            kill_switch=kill,
            reason=reason,
        )
