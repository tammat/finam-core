from __future__ import annotations

from dataclasses import dataclass
from itertools import product


@dataclass(frozen=True)
class ExitAlphaGridCandidate:
    stop_atr: float
    take_atr: float
    trail_atr: float
    max_bars_held: int
    policy_name: str


def build_exit_alpha_parameter_grid_v1() -> list[ExitAlphaGridCandidate]:
    result = []
    for stop_atr, take_atr, trail_atr, max_bars in product(
        [0.8, 1.0, 1.2],
        [1.4, 1.8, 2.2],
        [0.6, 0.8, 1.0],
        [6, 10, 14],
    ):
        result.append(
            ExitAlphaGridCandidate(
                stop_atr=stop_atr,
                take_atr=take_atr,
                trail_atr=trail_atr,
                max_bars_held=max_bars,
                policy_name=f"GRID_S{stop_atr}_T{take_atr}_TR{trail_atr}_H{max_bars}",
            )
        )
    return result
