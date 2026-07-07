from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MaxEdgeViewModel:
    current: dict
    ranking: list[dict]
    labels: dict
