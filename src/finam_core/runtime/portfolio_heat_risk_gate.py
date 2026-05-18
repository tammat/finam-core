from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PortfolioHeatDecision:
    allowed: bool
    reason: str
    margin_utilization_pct: float = 0.0
    drawdown: float = 0.0
    total_exposure: float = 0.0


class PortfolioHeatRiskGate:
    """Русский комментарий: блокирует новые сигналы при перегреве портфеля."""

    def __init__(self, conn: Any):
        self.conn = conn

    def check(
        self,
        *,
        max_margin_utilization_pct: float = 70.0,
        max_drawdown_abs: float = 10_000.0,
        max_total_exposure: float = 500_000.0,
    ) -> PortfolioHeatDecision:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                select
                    coalesce(margin_utilization_pct, 0),
                    coalesce(drawdown, 0),
                    coalesce(total_exposure, exposure, 0)
                from portfolio_snapshots
                order by ts desc
                limit 1
                """
            )
            row = cur.fetchone()

        if row is None:
            return PortfolioHeatDecision(True, "portfolio_snapshot_not_found")

        margin_utilization_pct = float(row[0] or 0)
        drawdown = float(row[1] or 0)
        total_exposure = float(row[2] or 0)

        if margin_utilization_pct >= max_margin_utilization_pct:
            return PortfolioHeatDecision(
                False,
                f"перегрев маржи; margin_utilization_pct={margin_utilization_pct:.2f}; limit={max_margin_utilization_pct:.2f}",
                margin_utilization_pct,
                drawdown,
                total_exposure,
            )

        if abs(drawdown) >= max_drawdown_abs:
            return PortfolioHeatDecision(
                False,
                f"превышена просадка; drawdown={drawdown:.2f}; limit={max_drawdown_abs:.2f}",
                margin_utilization_pct,
                drawdown,
                total_exposure,
            )

        if total_exposure >= max_total_exposure:
            return PortfolioHeatDecision(
                False,
                f"превышена экспозиция; total_exposure={total_exposure:.2f}; limit={max_total_exposure:.2f}",
                margin_utilization_pct,
                drawdown,
                total_exposure,
            )

        return PortfolioHeatDecision(
            True,
            "portfolio_heat_ok",
            margin_utilization_pct,
            drawdown,
            total_exposure,
        )
