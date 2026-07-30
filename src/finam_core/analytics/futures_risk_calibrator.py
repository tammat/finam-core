from __future__ import annotations

from dataclasses import dataclass
from math import ceil
import random


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
        "mae_q80_atr": quantile([item.mae_atr for item in valid], 0.80),
        "mfe_q70_atr": quantile([item.mfe_atr for item in valid], 0.70),
        "status": "INSUFFICIENT_DATA",
        "reason": f"requires trades>={min_trades}",
        "recommended_stop_atr": None,
        "recommended_take_atr": None,
        "recommended_volume_ratio": None,
        "counterfactual_expectancy_r": None,
        "counterfactual_lower_95_r": None,
        "counterfactual_drawdown_r": None,
        "promotion_eligible": False,
    }
    if len(valid) < min_trades:
        return result

    def path_r(item: TradePathObservation, stop: float, take: float) -> float:
        # With OHLC paths the order of MAE/MFE is unknown.  If both levels were
        # reachable, conservatively assume the stop happened first.
        if item.mae_atr >= stop:
            return -1.0
        if item.mfe_atr >= take:
            return take / stop
        return 0.0

    def drawdown(values: list[float]) -> float:
        equity = peak = worst = 0.0
        for value in values:
            equity += value
            peak = max(peak, equity)
            worst = max(worst, peak - equity)
        return worst

    def lower_95(values: list[float]) -> float:
        rng = random.Random(917)
        estimates = sorted(
            sum(rng.choice(values) for _ in values) / len(values)
            for _ in range(2000)
        )
        return estimates[int(0.05 * len(estimates))]

    candidates = []
    stop = bounds.min_stop_atr
    while stop <= bounds.max_stop_atr + 1e-9:
        minimum_take = max(bounds.prior_target_atr, bounds.min_reward_r * stop)
        for reward in (bounds.min_reward_r, bounds.min_reward_r + 0.5, bounds.min_reward_r + 1.0):
            take = max(minimum_take, stop * reward)
            values = [path_r(item, stop, take) for item in valid]
            candidates.append((lower_95(values), sum(values) / len(values), -drawdown(values), stop, take, values))
        stop = round(stop + 0.1, 10)
    best = max(candidates)
    lower_bound, expectancy, negative_dd, stop, take, _ = best

    # Volume is deliberately not optimized on winners.  Keep the incumbent
    # threshold until a separate forward comparison proves a change.
    volume = bounds.prior_volume_ratio

    result.update({
        "status": "CANDIDATE_FOR_REVIEW" if len(valid) >= 50 and lower_bound > 0 else "ADVISORY_READY",
        "reason": "ALL_TRADES_CONSERVATIVE_PATH_GRID_V2",
        "recommended_stop_atr": round(stop, 4),
        "recommended_take_atr": round(take, 4),
        "recommended_volume_ratio": round(volume, 4),
        "counterfactual_expectancy_r": round(expectancy, 6),
        "counterfactual_lower_95_r": round(lower_bound, 6),
        "counterfactual_drawdown_r": round(-negative_dd, 6),
        "promotion_eligible": len(valid) >= 50 and lower_bound > 0,
    })
    return result
