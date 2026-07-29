from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShadowOutcome:
    exit_price: float
    exit_reason: str
    net_r: float


def simulate_shadow(
    *, entry_price: float, side: str, atr: float, stop_atr: float, take_atr: float,
    bars: list[tuple[float, float, float]], roundtrip_cost_price: float = 0.0,
) -> ShadowOutcome | None:
    if entry_price <= 0 or atr <= 0 or stop_atr <= 0 or not bars:
        return None
    direction = 1.0 if side.upper() in {"LONG", "BUY"} else -1.0
    risk = atr * stop_atr
    stop = entry_price - direction * risk
    take = entry_price + direction * atr * take_atr
    exit_price, reason = bars[-1][2], "HORIZON_EXIT"
    for high, low, close in bars:
        stop_hit = low <= stop if direction > 0 else high >= stop
        take_hit = high >= take if direction > 0 else low <= take
        if stop_hit:  # conservative ordering when both are touched
            exit_price, reason = stop, "STOP"
            break
        if take_hit:
            exit_price, reason = take, "TAKE"
            break
    net_move = direction * (exit_price - entry_price) - max(0.0, roundtrip_cost_price)
    return ShadowOutcome(round(exit_price, 8), reason, round(net_move / risk, 8))


def max_drawdown(values: list[float]) -> float:
    equity = peak = worst = 0.0
    for value in values:
        equity += float(value)
        peak = max(peak, equity)
        worst = max(worst, peak - equity)
    return worst


def promotion_decision(actual_r: list[float], shadow_r: list[float], *, oos_size: int) -> dict:
    pairs = min(len(actual_r), len(shadow_r))
    if pairs < 80 or oos_size < 20:
        return {"promote": False, "reason": "INSUFFICIENT_PAIRED_OOS", "pairs": pairs, "oos_pairs": oos_size}
    actual = actual_r[-pairs:]; shadow = shadow_r[-pairs:]
    actual_exp = sum(actual) / pairs; shadow_exp = sum(shadow) / pairs
    actual_dd = max_drawdown(actual); shadow_dd = max_drawdown(shadow)
    actual_oos = sum(actual[-oos_size:]) / oos_size
    shadow_oos = sum(shadow[-oos_size:]) / oos_size
    positive = sorted((value for value in shadow if value > 0), reverse=True)
    concentration = (positive[0] / sum(positive)) if positive and sum(positive) > 0 else 1.0
    checks = {
        "expectancy_improvement": shadow_exp >= actual_exp + 0.10,
        "shadow_expectancy_positive": shadow_exp > 0,
        "drawdown_not_worse": shadow_dd <= actual_dd,
        "oos_positive": shadow_oos > 0,
        "oos_improvement": shadow_oos > actual_oos,
        "concentration_ok": concentration <= 0.35,
    }
    promote = all(checks.values())
    return {
        "promote": promote, "reason": "PROMOTE" if promote else "GUARD_NOT_PASSED",
        "pairs": pairs, "oos_pairs": oos_size, "actual_expectancy_r": actual_exp,
        "shadow_expectancy_r": shadow_exp, "actual_drawdown_r": actual_dd,
        "shadow_drawdown_r": shadow_dd, "actual_oos_r": actual_oos,
        "shadow_oos_r": shadow_oos, "largest_win_concentration": concentration, "checks": checks,
    }
