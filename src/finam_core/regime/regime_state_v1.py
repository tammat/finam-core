from __future__ import annotations

from dataclasses import dataclass


FAMILIES = ("TREND", "RANGE", "SHOCK")


@dataclass(frozen=True)
class RegimeProbabilityStateV1:
    trend_probability: float
    range_probability: float
    shock_probability: float
    candidate_family: str
    stable_family: str
    pending_family: str | None
    pending_count: int
    switched: bool


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def regime_probabilities_v1(
    *, mx_trend: str, mx_strength: float, rvi_regime: str,
    rvi_percentile: float,
) -> dict[str, float]:
    """Produce conservative family probabilities from causal MX/RVI features."""
    direction = str(mx_trend or "UNKNOWN").upper()
    volatility = str(rvi_regime or "NORMAL_VOL").upper()
    strength = _bounded(mx_strength)
    percentile = _bounded(rvi_percentile)

    trend_raw = (0.20 + 0.80 * strength) if direction in {"UP", "DOWN"} else 0.15
    range_raw = (0.30 + 0.70 * (1.0 - strength)) if direction == "RANGE" else (0.15 + 0.45 * (1.0 - strength))
    if volatility == "HIGH_VOL":
        shock_raw = 0.55 + 0.45 * percentile
    elif volatility == "NORMAL_VOL":
        shock_raw = 0.08 + 0.22 * percentile
    else:
        shock_raw = 0.03 + 0.07 * percentile

    total = trend_raw + range_raw + shock_raw
    return {
        "TREND": trend_raw / total,
        "RANGE": range_raw / total,
        "SHOCK": shock_raw / total,
    }


def resolve_regime_state_v1(
    *, probabilities: dict[str, float], previous_stable_family: str | None,
    previous_pending_family: str | None, previous_pending_count: int = 0,
    switch_probability: float = 0.60, confirmation_bars: int = 3,
) -> RegimeProbabilityStateV1:
    candidate = max(FAMILIES, key=lambda family: probabilities.get(family, 0.0))
    stable = str(previous_stable_family or candidate).upper()
    pending: str | None = None
    pending_count = 0
    switched = False

    if candidate != stable and probabilities[candidate] >= switch_probability:
        pending = candidate
        pending_count = previous_pending_count + 1 if previous_pending_family == candidate else 1
        if pending_count >= max(1, int(confirmation_bars)):
            stable = candidate
            pending = None
            pending_count = 0
            switched = True

    return RegimeProbabilityStateV1(
        trend_probability=probabilities["TREND"],
        range_probability=probabilities["RANGE"],
        shock_probability=probabilities["SHOCK"],
        candidate_family=candidate,
        stable_family=stable,
        pending_family=pending,
        pending_count=pending_count,
        switched=switched,
    )
