from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True, slots=True)
class ExitDecisionV1:
    exit_index: int
    reason_code: str


def _realized_volatility_bps(prices: Sequence[float], end: int, lookback: int) -> float:
    start = max(1, end - lookback + 1)
    changes = [prices[i] / prices[i - 1] - 1.0 for i in range(start, end + 1) if prices[i - 1] > 0]
    return statistics.pstdev(changes) * 10000.0 if len(changes) > 1 else 0.0


def entry_allowed_v1(
    prices: Sequence[float], volumes: Sequence[float], index: int, side: int, policy: dict,
) -> bool:
    if str(policy.get("entry_policy_code", "NONE")) != "META_ENTRY_V1":
        return True
    trend_lookback = int(policy.get("entry_trend_lookback", policy.get("trend_lookback", 20)))
    vol_lookback = int(policy.get("entry_volatility_lookback", policy.get("volatility_lookback", 10)))
    if index < max(trend_lookback, vol_lookback) or side == 0:
        return False
    trend = prices[index] / prices[index - trend_lookback] - 1.0
    volatility = _realized_volatility_bps(prices, index, vol_lookback)
    historical_volume = [float(value) for value in volumes[index - vol_lookback:index] if float(value) >= 0]
    average_volume = statistics.fmean(historical_volume) if historical_volume else 0.0
    volume_ratio = float(volumes[index]) / average_volume if average_volume > 0 else 0.0
    return (
        trend * side > 0
        and volatility >= float(policy.get("entry_min_volatility_bps", policy.get("min_volatility_bps", 0.0)))
        and volatility <= float(policy.get("entry_max_volatility_bps", policy.get("max_volatility_bps", 10000.0)))
        and volume_ratio >= float(policy.get("entry_min_volume_ratio", policy.get("min_volume_ratio", 0.0)))
    )


def dynamic_exit_v1(
    prices: Sequence[float], entry_index: int, side: int, max_holding_bars: int, policy: dict,
) -> ExitDecisionV1:
    final_index = min(len(prices) - 1, entry_index + max(1, int(max_holding_bars)))
    if str(policy.get("exit_policy_code", "FIXED_HOLD")) != "DYNAMIC_EXIT_V1":
        return ExitDecisionV1(final_index, "FIXED_HOLD")
    atr_lookback = int(policy.get("exit_atr_lookback", 14))
    start = max(1, entry_index - atr_lookback + 1)
    ranges = [abs(prices[i] - prices[i - 1]) for i in range(start, entry_index + 1)]
    atr = statistics.fmean(ranges) if ranges else max(abs(prices[entry_index]) * 0.0001, 1e-12)
    entry = prices[entry_index]
    stop_atr = float(policy.get("exit_stop_atr", 1.2))
    trail_atr = float(policy.get("exit_trail_atr", 1.0))
    trend_lookback = int(policy.get("exit_trend_lookback", 5))
    volatility_lookback = int(policy.get("exit_volatility_lookback", 10))
    volatility_multiplier = float(policy.get("exit_volatility_risk_multiplier", 2.0))
    minimum_bars = int(policy.get("exit_minimum_bars", 2))
    entry_volatility = max(_realized_volatility_bps(prices, entry_index, volatility_lookback), 1e-12)
    best = entry
    for index in range(entry_index + 1, final_index + 1):
        price = prices[index]
        best = max(best, price) if side > 0 else min(best, price)
        if (price - entry) * side <= -stop_atr * atr:
            return ExitDecisionV1(index, "ATR_STOP")
        if (best - entry) * side > 0 and (price - best) * side <= -trail_atr * atr:
            return ExitDecisionV1(index, "ATR_TRAIL")
        held = index - entry_index
        if held >= max(minimum_bars, trend_lookback) and (price - prices[index - trend_lookback]) * side <= 0:
            return ExitDecisionV1(index, "TREND_GONE")
        current_volatility = _realized_volatility_bps(prices, index, volatility_lookback)
        if held >= minimum_bars and current_volatility >= entry_volatility * volatility_multiplier and (price - entry) * side < 0:
            return ExitDecisionV1(index, "VOLATILITY_RISK")
    return ExitDecisionV1(final_index, "MAX_HOLD")
