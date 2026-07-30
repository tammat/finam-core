from __future__ import annotations

from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class Bar:
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class Variant:
    code: str
    entry_mode: str
    stop_atr: float
    take_atr: float
    trail_after_r: float | None = None
    trail_atr: float | None = None


@dataclass(frozen=True)
class Outcome:
    entered: bool
    entry_price: float | None
    exit_price: float | None
    reason: str
    net_r: float | None


def default_variants(strategy: str) -> tuple[Variant, ...]:
    """Small, auditable search space; deliberately not a curve-fitting grid."""
    mean_reversion = strategy.upper() == "MEAN_REVERSION_EQUITY"
    stops = (1.2, 1.5, 1.8) if mean_reversion else (1.5, 1.9, 2.3)
    rewards = (1.1, 1.4, 1.8) if mean_reversion else (1.6, 2.0, 2.4)
    result: list[Variant] = []
    for entry_mode in ("IMMEDIATE", "CONFIRM_1", "RETEST_3"):
        for stop, reward in zip(stops, rewards):
            result.append(Variant(
                f"{entry_mode}_S{stop:.1f}_R{reward:.1f}", entry_mode,
                stop, stop * reward,
                trail_after_r=1.0 if not mean_reversion else 1.2,
                trail_atr=1.0 if not mean_reversion else 0.8,
            ))
    return tuple(result)


def _entry(entry_mode: str, signal_price: float, side: str, bars: list[Bar]) -> tuple[int, float] | None:
    if not bars:
        return None
    direction = 1 if side.upper() in {"LONG", "BUY"} else -1
    if entry_mode == "IMMEDIATE":
        return 0, signal_price
    if entry_mode == "CONFIRM_1":
        return (0, bars[0].close) if direction * (bars[0].close - signal_price) > 0 else None
    if entry_mode == "RETEST_3":
        for index, bar in enumerate(bars[:3]):
            touched = bar.low <= signal_price <= bar.high
            confirmed = direction * (bar.close - signal_price) >= 0
            if touched and confirmed:
                return index, signal_price
        return None
    raise ValueError(f"unknown entry mode: {entry_mode}")


def simulate_variant(*, signal_price: float, side: str, atr: float,
                     bars: list[Bar], variant: Variant,
                     roundtrip_cost_price: float = 0.0) -> Outcome:
    if signal_price <= 0 or atr <= 0 or not bars:
        return Outcome(False, None, None, "INVALID_INPUT", None)
    selected = _entry(variant.entry_mode, signal_price, side, bars)
    if selected is None:
        return Outcome(False, None, None, "ENTRY_FILTERED", None)
    start, entry = selected
    direction = 1 if side.upper() in {"LONG", "BUY"} else -1
    risk = atr * variant.stop_atr
    stop = entry - direction * risk
    take = entry + direction * atr * variant.take_atr
    best = entry
    exit_price, reason = bars[-1].close, "HORIZON_MARK"
    for bar in bars[start:]:
        best = max(best, bar.high) if direction > 0 else min(best, bar.low)
        if variant.trail_after_r is not None and direction * (best - entry) >= risk * variant.trail_after_r:
            distance = atr * float(variant.trail_atr or 1.0)
            candidate = best - direction * distance
            stop = max(stop, candidate) if direction > 0 else min(stop, candidate)
        stop_hit = bar.low <= stop if direction > 0 else bar.high >= stop
        take_hit = bar.high >= take if direction > 0 else bar.low <= take
        if stop_hit:  # conservative if both levels were inside one candle
            exit_price, reason = stop, "TRAIL_OR_STOP"
            break
        if take_hit:
            exit_price, reason = take, "TAKE"
            break
    net_r = (direction * (exit_price - entry) - max(0.0, roundtrip_cost_price)) / risk
    return Outcome(True, round(entry, 8), round(exit_price, 8), reason, round(net_r, 8))


def max_drawdown_r(values: list[float]) -> float:
    equity = peak = worst = 0.0
    for value in values:
        equity += float(value)
        peak = max(peak, equity)
        worst = max(worst, peak - equity)
    return worst


def evaluate_walk_forward(rows: list[dict], *, min_pairs: int = 80,
                          min_oos: int = 20) -> dict:
    """Rank only by the chronological OOS tail and apply promotion guards."""
    entered = [row for row in rows if row.get("shadow_r") is not None]
    if len(entered) < min_pairs:
        return {"status": "SHADOW_ACCUMULATION", "pairs": len(entered),
                "reason": f"requires paired trades>={min_pairs}"}
    oos_size = max(min_oos, len(entered) // 5)
    oos = entered[-oos_size:]
    actual = [float(row["actual_r"]) for row in entered]
    shadow = [float(row["shadow_r"]) for row in entered]
    actual_oos = [float(row["actual_r"]) for row in oos]
    shadow_oos = [float(row["shadow_r"]) for row in oos]
    wins = sorted((value for value in shadow if value > 0), reverse=True)
    concentration = wins[0] / sum(wins) if wins and sum(wins) else 1.0
    checks = {
        "expectancy_gain": mean(shadow) >= mean(actual) + 0.10,
        "shadow_expectancy_positive": mean(shadow) > 0,
        "drawdown_not_worse": max_drawdown_r(shadow) <= max_drawdown_r(actual),
        "oos_positive": mean(shadow_oos) > 0,
        "oos_better": mean(shadow_oos) > mean(actual_oos),
        "largest_win_concentration": concentration <= 0.35,
    }
    return {
        "status": "READY_FOR_PAPER_CONFIRMATION" if all(checks.values()) else "KEEP_SHADOW",
        "pairs": len(entered), "oos_pairs": oos_size,
        "actual_expectancy_r": mean(actual), "shadow_expectancy_r": mean(shadow),
        "actual_oos_r": mean(actual_oos), "shadow_oos_r": mean(shadow_oos),
        "actual_drawdown_r": max_drawdown_r(actual),
        "shadow_drawdown_r": max_drawdown_r(shadow),
        "largest_win_concentration": concentration, "checks": checks,
    }


def evaluate_paper_challenger(rows: list[dict], *, min_pairs: int = 30,
                              min_oos: int = 10) -> dict:
    """Forward-only champion/challenger decision after the challenger was selected."""
    entered = [row for row in rows if row.get("shadow_r") is not None]
    if len(entered) < min_pairs:
        return {"status": "PAPER_CHALLENGER", "pairs": len(entered), "oos_pairs": 0,
                "reason": f"requires forward paired trades>={min_pairs}"}
    oos_size = max(min_oos, len(entered) // 5)
    actual = [float(row["actual_r"]) for row in entered]
    shadow = [float(row["shadow_r"]) for row in entered]
    actual_oos, shadow_oos = actual[-oos_size:], shadow[-oos_size:]
    wins = sorted((value for value in shadow if value > 0), reverse=True)
    concentration = wins[0] / sum(wins) if wins and sum(wins) else 1.0
    checks = {
        "expectancy_improvement": mean(shadow) >= mean(actual) + 0.05,
        "shadow_expectancy_positive": mean(shadow) > 0,
        "drawdown_not_worse": max_drawdown_r(shadow) <= max_drawdown_r(actual),
        "oos_positive": mean(shadow_oos) > 0,
        "oos_improvement": mean(shadow_oos) > mean(actual_oos),
        "concentration_ok": concentration <= 0.35,
    }
    return {
        "status": "READY_FOR_CHAMPION_CONFIRMATION" if all(checks.values()) else "KEEP_PAPER_CHALLENGER",
        "pairs": len(entered), "oos_pairs": oos_size,
        "actual_expectancy_r": mean(actual), "challenger_expectancy_r": mean(shadow),
        "expectancy_delta_r": mean(shadow) - mean(actual),
        "actual_oos_r": mean(actual_oos), "challenger_oos_r": mean(shadow_oos),
        "actual_drawdown_r": max_drawdown_r(actual),
        "challenger_drawdown_r": max_drawdown_r(shadow),
        "largest_win_concentration": concentration, "checks": checks,
    }


def evaluate_active_paper_champion(
    rows: list[dict], *, validated_drawdown_r: float | None = None,
    min_soft_trades: int = 20, min_hard_trades: int = 10,
) -> dict:
    """Absolute Paper-only health guard for an already promoted Champion."""
    values = [float(row["actual_r"]) for row in rows if row.get("actual_r") is not None]
    trades = len(values)
    expectancy = mean(values) if values else 0.0
    drawdown = max_drawdown_r(values)
    gross_profit = sum(value for value in values if value > 0)
    gross_loss = abs(sum(value for value in values if value < 0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)
    validated = max(0.0, float(validated_drawdown_r or 0.0))
    hard_drawdown_limit = max(3.0, validated * 1.25)
    hard_breach = trades >= min_hard_trades and drawdown > hard_drawdown_limit
    soft_breach = trades >= min_soft_trades and (expectancy <= -0.10 or profit_factor < 0.80)
    if hard_breach:
        status, reason = "ROLLBACK_NOW", "HARD_DRAWDOWN_BREACH"
    elif soft_breach:
        status, reason = "DEGRADED", "NEGATIVE_EXPECTANCY_OR_LOW_PF"
    elif trades < min_soft_trades:
        status, reason = "MONITOR", f"requires champion trades>={min_soft_trades}"
    else:
        status, reason = "HEALTHY", "CHAMPION_GUARDS_PASS"
    return {
        "status": status, "reason": reason, "trades": trades,
        "expectancy_r": expectancy, "profit_factor": profit_factor,
        "drawdown_r": drawdown, "hard_drawdown_limit_r": hard_drawdown_limit,
        "hard_breach": hard_breach, "soft_breach": soft_breach,
    }
