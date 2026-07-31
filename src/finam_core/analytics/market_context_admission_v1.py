from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import math


@dataclass(frozen=True)
class MarketContextAdmissionV1:
    mode: str
    shadow_allowed: bool
    paper_allowed: bool
    reason: str


def decide_market_context_admission_v1(
    *,
    now: datetime,
    index_bar_ts: datetime | None,
    rvi_bar_ts: datetime | None,
    index_max_age_seconds: int = 600,
    rvi_max_age_seconds: int = 1800,
) -> MarketContextAdmissionV1:
    """Fail closed for Paper while preserving honest Shadow observations."""
    index_fresh = bool(
        index_bar_ts
        and 0 <= (now - index_bar_ts).total_seconds() <= index_max_age_seconds
    )
    rvi_fresh = bool(
        rvi_bar_ts
        and 0 <= (now - rvi_bar_ts).total_seconds() <= rvi_max_age_seconds
    )
    if index_fresh and rvi_fresh:
        return MarketContextAdmissionV1("FULL", True, True, "INDEX_AND_RVI_FRESH")
    if index_fresh:
        return MarketContextAdmissionV1(
            "INDEX_ONLY", True, False, "RVI_NOT_FRESH_PAPER_BLOCKED"
        )
    return MarketContextAdmissionV1(
        "UNAVAILABLE", False, False, "INDEX_NOT_FRESH_ALL_BLOCKED"
    )


def independent_candidate_key_v1(
    *,
    strategy: str,
    symbol: str,
    side: str,
    event_ts: datetime,
    price: float,
    atr: float,
    regime: str,
    futures: bool,
) -> str:
    """Stable pre-persistence embargo key with a 0.5 ATR movement exception."""
    window_seconds = 900 if futures else 1800
    bucket = int(event_ts.timestamp()) // window_seconds
    movement = max(abs(float(atr)) * 0.5, abs(float(price)) * 0.0001, 1e-9)
    price_band = math.floor(float(price) / movement)
    raw = "|".join(
        (
            str(strategy),
            str(symbol),
            str(side).upper(),
            str(bucket),
            str(price_band),
            str(regime or "UNKNOWN").upper(),
        )
    )
    return "pre-signal:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
