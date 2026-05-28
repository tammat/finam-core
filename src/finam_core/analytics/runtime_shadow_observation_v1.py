from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShadowObservationRowV1:
    symbol: str
    side: str
    hour_msk: int
    allowed: bool
    expectancy_points: float
    pnl_points: float
    closed_trades: int
    shadow_block_candidate: bool
    decay_state: str


class RuntimeShadowObservationV1:
    """
    Русский комментарий:
    Shadow-режим runtime governance.
    Ничего не блокирует, только оценивает потенциальные блокировки.
    """

    def evaluate(
        self,
        *,
        symbol: str,
        side: str,
        hour_msk: int,
        expectancy_points: float,
        pnl_points: float,
        closed_trades: int,
    ) -> ShadowObservationRowV1:
        decay_state = "DECAY" if expectancy_points <= 0 else "HEALTHY"

        shadow_block_candidate = (
            expectancy_points <= 0
            and closed_trades >= 30
        )

        return ShadowObservationRowV1(
            symbol=symbol,
            side=side,
            hour_msk=hour_msk,
            allowed=True,
            expectancy_points=expectancy_points,
            pnl_points=pnl_points,
            closed_trades=closed_trades,
            shadow_block_candidate=shadow_block_candidate,
            decay_state=decay_state,
        )
