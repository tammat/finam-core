# -*- coding: utf-8 -*-
"""
BAR VOLUME features.
Русский комментарий: слой только считает признаки объёма, заявки не отправляет.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BarVolumeFeatures:
    current_volume: float
    avg_volume: float
    rel_volume: float
    volume_confirmed: bool
    reason: str


class BarVolumeFeatureEngine:
    def __init__(self, lookback: int = 20, confirm_ratio: float = 1.5) -> None:
        self.lookback = int(lookback)
        self.confirm_ratio = float(confirm_ratio)

    def evaluate(self, bars: list[dict]) -> BarVolumeFeatures:
        if not bars:
            return BarVolumeFeatures(0.0, 0.0, 0.0, False, "no_bars")

        current_volume = float(bars[-1].get("volume", 0.0) or 0.0)
        history = bars[-self.lookback - 1:-1]

        volumes = [
            float(x.get("volume", 0.0) or 0.0)
            for x in history
            if float(x.get("volume", 0.0) or 0.0) > 0
        ]

        if current_volume <= 0:
            return BarVolumeFeatures(current_volume, 0.0, 0.0, False, "no_current_volume")

        if not volumes:
            return BarVolumeFeatures(current_volume, 0.0, 0.0, False, "no_volume_history")

        avg_volume = sum(volumes) / len(volumes)
        rel_volume = current_volume / avg_volume if avg_volume > 0 else 0.0
        confirmed = rel_volume >= self.confirm_ratio

        return BarVolumeFeatures(
            current_volume=current_volume,
            avg_volume=avg_volume,
            rel_volume=rel_volume,
            volume_confirmed=confirmed,
            reason="volume_confirmed" if confirmed else "volume_too_low",
        )
