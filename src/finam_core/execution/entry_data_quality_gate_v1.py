from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class EntryDataQualityDecisionV1:
    allowed: bool
    reason_code: str
    latest_bar_age_seconds: float | None = None
    maximum_gap_seconds: float | None = None


def timeframe_seconds(timeframe: str) -> int:
    return {"M1": 60, "M5": 300}.get(str(timeframe or "").upper(), 300)


def evaluate_entry_data_quality_v1(
    *,
    timeframe: str,
    completed_bar_times: list[datetime],
    session_open: bool,
    is_futures: bool,
    cost_verified_at: datetime | None,
    now: datetime | None = None,
    cost_max_age_seconds: int = 172800,
) -> EntryDataQualityDecisionV1:
    """Fail-closed admission using only completed, continuous market bars."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    if not session_open:
        return EntryDataQualityDecisionV1(False, "MARKET_SESSION_CLOSED")

    interval = timeframe_seconds(timeframe)
    bars = sorted(
        value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        for value in completed_bar_times
    )
    if len(bars) < 3:
        return EntryDataQualityDecisionV1(False, "COMPLETED_BARS_INSUFFICIENT")

    age = (current - bars[-1].astimezone(timezone.utc)).total_seconds()
    maximum_age = 180 if interval == 60 else 420
    if age < interval:
        return EntryDataQualityDecisionV1(False, "BAR_NOT_CLOSED", age)
    if age > maximum_age:
        return EntryDataQualityDecisionV1(False, "COMPLETED_BAR_STALE", age)

    gaps = [(right - left).total_seconds() for left, right in zip(bars, bars[1:])]
    maximum_gap = max(gaps, default=0.0)
    if maximum_gap > interval * 1.5:
        return EntryDataQualityDecisionV1(False, "COMPLETED_BAR_SEQUENCE_GAP", age, maximum_gap)

    if is_futures:
        if cost_verified_at is None:
            return EntryDataQualityDecisionV1(False, "CONTRACT_COST_SPEC_MISSING", age, maximum_gap)
        verified = cost_verified_at
        if verified.tzinfo is None:
            verified = verified.replace(tzinfo=timezone.utc)
        if (current - verified.astimezone(timezone.utc)).total_seconds() > cost_max_age_seconds:
            return EntryDataQualityDecisionV1(False, "CONTRACT_COST_SPEC_STALE", age, maximum_gap)

    return EntryDataQualityDecisionV1(True, "ENTRY_DATA_QUALITY_PASS", age, maximum_gap)
