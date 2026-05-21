from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class TradeQuality:
    trade_index: int
    pnl: float
    mfe: float
    mae: float
    efficiency: float


def calculate_trade_quality(
    pnls: Iterable[float],
    mfes: Iterable[float],
    maes: Iterable[float],
) -> list[TradeQuality]:

    pnl_values = [float(x) for x in pnls]
    mfe_values = [float(x) for x in mfes]
    mae_values = [float(x) for x in maes]

    result: list[TradeQuality] = []

    for idx, (pnl, mfe, mae) in enumerate(
        zip(pnl_values, mfe_values, mae_values),
        start=1,
    ):
        efficiency = 0.0

        if mfe > 0:
            efficiency = pnl / mfe

        result.append(
            TradeQuality(
                trade_index=idx,
                pnl=round(pnl, 10),
                mfe=round(mfe, 10),
                mae=round(mae, 10),
                efficiency=round(efficiency, 10),
            )
        )

    return result
