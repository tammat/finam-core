from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class EquityPoint:
    trade_index: int
    pnl: float
    cumulative_pnl: float
    peak_equity: float
    drawdown: float


def build_equity_curve(
    pnls: Iterable[float],
) -> list[EquityPoint]:
    """
    Строит equity curve и drawdown timeline.
    """

    result: list[EquityPoint] = []

    cumulative = 0.0
    peak = 0.0

    for idx, pnl in enumerate(pnls, start=1):
        cumulative += float(pnl)

        peak = max(peak, cumulative)

        drawdown = cumulative - peak

        result.append(
            EquityPoint(
                trade_index=idx,
                pnl=round(float(pnl), 10),
                cumulative_pnl=round(cumulative, 10),
                peak_equity=round(peak, 10),
                drawdown=round(drawdown, 10),
            )
        )

    return result
