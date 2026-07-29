from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from statistics import median


@dataclass(frozen=True)
class CalibrationBounds:
    min_stop_atr: float
    max_stop_atr: float
    prior_target_atr: float
    min_reward_r: float
    prior_volume_ratio: float


@dataclass(frozen=True)
class TradePathObservation:
    profitable: bool
    mae_atr: float
    mfe_atr: float
    volume_ratio: float | None = None


def quantile(values: list[float], probability: float) -> float | None:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    probability = min(1.0, max(0.0, float(probability)))
    index = (len(ordered) - 1) * probability
    lower = int(index)
    upper = min(len(ordered) - 1, ceil(index))
    if lower == upper:
        return ordered[lower]
    weight = index - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def calibrate_profile(
    observations: list[TradePathObservation],
    bounds: CalibrationBounds,
    *,
    min_trades: int = 20,
    min_winners: int = 8,
) -> dict:
    valid = [item for item in observations if item.mae_atr >= 0 and item.mfe_atr >= 0]
    winners = [item for item in valid if item.profitable]
    result = {
        "trades": len(valid),
        "winners": len(winners),
        "mae_q80_atr": quantile([item.mae_atr for item in winners], 0.80),
        "mfe_q70_atr": quantile([item.mfe_atr for item in winners], 0.70),
        "status": "INSUFFICIENT_DATA",
        "reason": f"requires trades>={min_trades} and winners>={min_winners}",
        "recommended_stop_atr": None,
        "recommended_take_atr": None,
        "recommended_volume_ratio": None,
    }
    if len(valid) < min_trades or len(winners) < min_winners:
        return result

    raw_stop = float(result["mae_q80_atr"] or bounds.min_stop_atr) + 0.10
    stop = min(bounds.max_stop_atr, max(bounds.min_stop_atr, raw_stop))
    raw_take = float(result["mfe_q70_atr"] or bounds.prior_target_atr)
    take = max(bounds.prior_target_atr, bounds.min_reward_r * stop, raw_take)
    take = min(max(bounds.prior_target_atr * 1.5, bounds.min_reward_r * stop), take)

    winner_volumes = [item.volume_ratio for item in winners if item.volume_ratio is not None]
    volume = bounds.prior_volume_ratio
    if len(winner_volumes) >= min_winners:
        volume = min(2.0, max(1.0, float(median(winner_volumes))))

    result.update({
        "status": "CANDIDATE_FOR_REVIEW" if len(valid) >= 50 else "ADVISORY_READY",
        "reason": "MAE_Q80_PLUS_BUFFER_AND_MFE_Q70",
        "recommended_stop_atr": round(stop, 4),
        "recommended_take_atr": round(take, 4),
        "recommended_volume_ratio": round(volume, 4),
    })
    return result
