from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class SmartMoneyFeatures:
    symbol: str
    rvol: float
    tick_velocity: float
    price_velocity: float
    range_pct: float
    absorption_score: float
    sweep_reclaim_score: float
    impulse_score: float
    smart_money_score: float
    label: str


class SmartMoneyFeatureLayer:
    """Русский комментарий: лёгкий order-flow слой без DOM/HFT."""

    def __init__(self, window: int = 20) -> None:
        self.window = int(window)
        self.prices: dict[str, deque[float]] = {}
        self.volumes: dict[str, deque[float]] = {}
        self.tick_counts: dict[str, deque[int]] = {}

    def update(
        self,
        symbol: str,
        price: float,
        volume: float,
        high: float | None = None,
        low: float | None = None,
        avg_volume: float | None = None,
    ) -> SmartMoneyFeatures:
        price = float(price)
        volume = float(volume or 0.0)
        high = float(high if high is not None else price)
        low = float(low if low is not None else price)

        prices = self.prices.setdefault(symbol, deque(maxlen=self.window))
        volumes = self.volumes.setdefault(symbol, deque(maxlen=self.window))
        ticks = self.tick_counts.setdefault(symbol, deque(maxlen=self.window))

        prev_price = prices[-1] if prices else price

        prices.append(price)
        volumes.append(volume)
        ticks.append(1)

        avg_vol = float(avg_volume or (sum(volumes) / max(len(volumes), 1)) or 1.0)

        rvol = volume / avg_vol if avg_vol > 0 else 0.0
        tick_velocity = sum(ticks) / max(len(ticks), 1)
        price_velocity = abs(price - prev_price) / prev_price if prev_price > 0 else 0.0
        range_pct = abs(high - low) / price if price > 0 else 0.0

        # Русский комментарий: absorption = большой объём при узком диапазоне.
        absorption_score = 0.0
        if rvol >= 2.0 and range_pct <= 0.004:
            absorption_score = min((rvol / 5.0) * (0.004 / max(range_pct, 0.0001)), 1.0)

        # Русский комментарий: sweep/reclaim proxy = большой диапазон и возврат к середине.
        mid = (high + low) / 2.0
        reclaim_strength = 1.0 - min(abs(price - mid) / max(high - low, 0.0001), 1.0)
        sweep_reclaim_score = 0.0
        if rvol >= 1.5 and range_pct >= 0.008:
            sweep_reclaim_score = min(reclaim_strength * (rvol / 4.0), 1.0)

        # Русский комментарий: impulse = объём + скорость цены + расширение диапазона.
        impulse_score = min(
            (min(rvol / 3.0, 1.0) * 0.45)
            + (min(price_velocity / 0.01, 1.0) * 0.30)
            + (min(range_pct / 0.015, 1.0) * 0.25),
            1.0,
        )

        smart_money_score = round(
            absorption_score * 0.35
            + sweep_reclaim_score * 0.25
            + impulse_score * 0.40,
            6,
        )

        if smart_money_score >= 0.70:
            label = "INSTITUTIONAL_GRADE"
        elif smart_money_score >= 0.45:
            label = "SMART_MONEY_CANDIDATE"
        else:
            label = "NORMAL_FLOW"

        return SmartMoneyFeatures(
            symbol=symbol,
            rvol=round(rvol, 6),
            tick_velocity=round(tick_velocity, 6),
            price_velocity=round(price_velocity, 6),
            range_pct=round(range_pct, 6),
            absorption_score=round(absorption_score, 6),
            sweep_reclaim_score=round(sweep_reclaim_score, 6),
            impulse_score=round(impulse_score, 6),
            smart_money_score=smart_money_score,
            label=label,
        )
