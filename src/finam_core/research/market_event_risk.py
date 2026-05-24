from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class MarketEventRiskDecision:
    status: str
    allow_runtime: bool
    risk_multiplier: float
    reason: str


def decide_market_event_risk(
    *,
    now: datetime,
    nearest_event_ts: datetime | None,
    impact: str | None,
    minutes_before: int = 60,
    minutes_after: int = 30,
) -> MarketEventRiskDecision:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    if nearest_event_ts is None:
        return MarketEventRiskDecision("NORMAL", True, 1.0, "нет_значимых_событий")

    if nearest_event_ts.tzinfo is None:
        nearest_event_ts = nearest_event_ts.replace(tzinfo=timezone.utc)

    delta_min = (nearest_event_ts - now).total_seconds() / 60
    impact_norm = str(impact or "").upper()

    if impact_norm in {"HIGH", "CRITICAL"} and -minutes_after <= delta_min <= minutes_before:
        return MarketEventRiskDecision(
            "EVENT_ACTIVE",
            False,
            0.0,
            f"рядом_важное_событие impact={impact_norm} delta_min={round(delta_min, 1)}",
        )

    if impact_norm == "MEDIUM" and 0 <= delta_min <= minutes_before:
        return MarketEventRiskDecision(
            "EVENT_SOON",
            True,
            0.5,
            f"среднее_событие_скоро delta_min={round(delta_min, 1)}",
        )

    return MarketEventRiskDecision("NORMAL", True, 1.0, "событие_не_ограничивает_торговлю")
