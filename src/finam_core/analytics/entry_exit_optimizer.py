from __future__ import annotations

from dataclasses import dataclass
import random
import math
from statistics import mean


@dataclass(frozen=True)
class Bar:
    high: float
    low: float
    close: float
    open: float | None = None
    volume: float | None = None


@dataclass(frozen=True)
class EntryContext:
    """Only information available before the candidate entry decision."""
    atr_percentile: float = 0.5
    relative_volume: float = 1.0
    regime: str = "UNKNOWN"
    cost_to_atr: float = 0.0
    strategy: str = ""


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
    entry_decision: str = "UNKNOWN"
    entry_decision_reason: str = "NOT_AUDITED"


def default_variants(strategy: str) -> tuple[Variant, ...]:
    """Small, auditable search space; deliberately not a curve-fitting grid."""
    mean_reversion = strategy.upper() == "MEAN_REVERSION_EQUITY"
    stops = (1.2, 1.5, 1.8) if mean_reversion else (1.5, 1.9, 2.3)
    rewards = (1.1, 1.4, 1.8) if mean_reversion else (1.6, 2.0, 2.4)
    result: list[Variant] = []
    for entry_mode in ("IMMEDIATE", "CONFIRM_1", "RETEST_3", "ADAPTIVE"):
        for stop, reward in zip(stops, rewards):
            result.append(Variant(
                f"{entry_mode}_S{stop:.1f}_R{reward:.1f}", entry_mode,
                stop, stop * reward,
                trail_after_r=1.0 if not mean_reversion else 1.2,
                trail_atr=1.0 if not mean_reversion else 0.8,
            ))
    return tuple(result)


def adaptive_entry_decision(context: EntryContext, *, take_atr: float) -> tuple[str, str]:
    """Route a signal using orthogonal, pre-entry features; fail closed."""
    regime = context.regime.upper()
    rel_volume = max(0.0, context.relative_volume)
    atr_percentile = min(1.0, max(0.0, context.atr_percentile))
    cost_to_atr = max(0.0, context.cost_to_atr)

    # Do not enter if even the nominal target has too little room after costs.
    if rel_volume < 0.60:
        return "SKIP", "LOW_RELATIVE_VOLUME"
    if cost_to_atr >= max(0.20, take_atr * 0.20):
        return "SKIP", "COST_TOO_HIGH_FOR_TARGET"
    is_range = "RANGE" in regime
    is_trend = "TREND" in regime and not is_range
    if is_range:
        return (("RETEST_3", "RANGE_MEAN_REVERSION")
                if context.strategy.upper() == "MEAN_REVERSION_EQUITY"
                else ("SKIP", "RANGE_BLOCKS_BREAKOUT"))
    if atr_percentile >= 0.85:
        return "CONFIRM_1", "EXTREME_VOLATILITY"
    if is_trend and rel_volume >= 1.25 and 0.20 <= atr_percentile < 0.80:
        return "IMMEDIATE", "STRONG_TREND_AND_VOLUME"
    return "RETEST_3", "NORMAL_CONTEXT_WAIT_RETEST"


def adaptive_entry_mode(context: EntryContext, *, take_atr: float) -> str:
    return adaptive_entry_decision(context, take_atr=take_atr)[0]


def _entry(entry_mode: str, signal_price: float, side: str, bars: list[Bar], *,
           atr: float, context: EntryContext | None = None,
           take_atr: float = 0.0) -> tuple[tuple[int, float] | None, str, str]:
    if not bars:
        return None, entry_mode, "NO_FUTURE_BARS"
    direction = 1 if side.upper() in {"LONG", "BUY"} else -1
    adaptive_retest = False
    decision_reason = "FIXED_ENTRY_MODE"
    if entry_mode == "ADAPTIVE":
        entry_mode, decision_reason = adaptive_entry_decision(
            context or EntryContext(), take_atr=take_atr)
        if entry_mode == "SKIP":
            return None, entry_mode, decision_reason
        adaptive_retest = entry_mode == "RETEST_3"
    if entry_mode == "IMMEDIATE":
        return (0, signal_price), entry_mode, decision_reason
    if entry_mode == "CONFIRM_1":
        # Confirmation is only known at the close.  The confirmation candle
        # cannot also stop or take a position that did not exist intrabar.
        selected = ((1, bars[0].close)
                    if direction * (bars[0].close - signal_price) > 0 else None)
        reason = decision_reason if selected else f"{decision_reason}:CONFIRMATION_FAILED"
        return selected, entry_mode, reason
    if entry_mode == "RETEST_3":
        for index, bar in enumerate(bars[:3]):
            if adaptive_retest:
                favourable = (bar.high - signal_price if direction > 0
                              else signal_price - bar.low)
                # If one completed candle both runs away and revisits the
                # level, its intrabar order is unknowable: reject it.
                if favourable > atr * 0.70:
                    return None, entry_mode, f"{decision_reason}:RUNAWAY_OR_AMBIGUOUS_BAR"
                touched = (bar.low <= signal_price + atr * 0.20 if direction > 0
                           else bar.high >= signal_price - atr * 0.20)
            else:
                touched = bar.low <= signal_price <= bar.high
            confirmed = direction * (bar.close - signal_price) >= 0
            if touched and confirmed:
                # A retest is confirmed at the close, so use that observable
                # price and start exit evaluation on the following candle.
                return (index + 1, bar.close), entry_mode, decision_reason
        return None, entry_mode, f"{decision_reason}:RETEST_NOT_CONFIRMED"
    raise ValueError(f"unknown entry mode: {entry_mode}")


def simulate_variant(*, signal_price: float, side: str, atr: float,
                     bars: list[Bar], variant: Variant,
                     entry_context: EntryContext | None = None,
                     roundtrip_cost_price: float = 0.0,
                     tick_size: float = 0.0,
                     stop_slippage_ticks: float = 0.0) -> Outcome:
    if signal_price <= 0 or atr <= 0 or not bars:
        return Outcome(False, None, None, "INVALID_INPUT", None)
    selected, entry_decision, entry_decision_reason = _entry(
        variant.entry_mode, signal_price, side, bars, atr=atr,
        context=entry_context, take_atr=variant.take_atr)
    if selected is None:
        return Outcome(False, None, None, "ENTRY_FILTERED", None,
                       entry_decision, entry_decision_reason)
    start, entry = selected
    direction = 1 if side.upper() in {"LONG", "BUY"} else -1
    risk = atr * variant.stop_atr
    stop = entry - direction * risk
    take = entry + direction * atr * variant.take_atr
    best = entry
    exit_price, reason = bars[-1].close, "HORIZON_MARK"
    for bar in bars[start:]:
        # `stop` is based only on earlier completed candles.  Raising it from
        # this candle's favourable extreme before inspecting its adverse
        # extreme would assume an unknowable high/low order.
        stop_hit = bar.low <= stop if direction > 0 else bar.high >= stop
        take_hit = bar.high >= take if direction > 0 else bar.low <= take
        if stop_hit:  # conservative if both levels were inside one candle
            opened = float(bar.open if bar.open is not None else bar.close)
            gap_fill = min(stop, opened) if direction > 0 else max(stop, opened)
            exit_price = gap_fill - direction * max(0.0, tick_size) * max(0.0, stop_slippage_ticks)
            if tick_size > 0:
                units = exit_price / tick_size
                exit_price = (math.floor(units) if direction > 0 else math.ceil(units)) * tick_size
            reason = "GAP_STOP" if gap_fill != stop else "TRAIL_OR_STOP"
            break
        if take_hit:
            # A limit target receives no favourable gap improvement: assuming
            # the exact target is more conservative and avoids phantom edge.
            exit_price, reason = take, "TAKE"
            break
        best = max(best, bar.high) if direction > 0 else min(best, bar.low)
        if variant.trail_after_r is not None and direction * (best - entry) >= risk * variant.trail_after_r:
            distance = atr * float(variant.trail_atr or 1.0)
            candidate = best - direction * distance
            stop = max(stop, candidate) if direction > 0 else min(stop, candidate)
    net_r = (direction * (exit_price - entry) - max(0.0, roundtrip_cost_price)) / risk
    return Outcome(True, round(entry, 8), round(exit_price, 8), reason, round(net_r, 8),
                   entry_decision, entry_decision_reason)


def max_drawdown_r(values: list[float]) -> float:
    equity = peak = worst = 0.0
    for value in values:
        equity += float(value)
        peak = max(peak, equity)
        worst = max(worst, peak - equity)
    return worst


def bootstrap_lower_mean(values: list[float], *, confidence: float = 0.95,
                         samples: int = 2000, seed: int = 517) -> float:
    """Deterministic non-parametric lower bound for mean performance."""
    if not values:
        return float("-inf")
    rng = random.Random(seed)
    size = len(values)
    estimates = sorted(mean(rng.choice(values) for _ in range(size)) for _ in range(samples))
    index = max(0, min(len(estimates) - 1, int((1.0 - confidence) * len(estimates))))
    return float(estimates[index])


def regime_sample_check(rows: list[dict], *, minimum: int) -> tuple[bool, dict[str, int]]:
    counts: dict[str, int] = {}
    for row in rows:
        regime = str(row.get("regime") or "UNKNOWN").upper()
        if regime != "UNKNOWN":
            counts[regime] = counts.get(regime, 0) + 1
    return bool(counts) and min(counts.values()) >= minimum, counts


def negative_control_check(rows: list[dict], *, confidence: float = 0.95) -> dict:
    """Require the candidate to beat a causal, unconditional next-bar entry.

    The control is evaluated on the same signal, horizon, stop, target and
    costs.  Only its entry timing ignores the strategy condition.  Missing
    controls fail closed once this gate is used for promotion.
    """
    paired = [row for row in rows
              if row.get("shadow_r") is not None and row.get("placebo_r") is not None]
    if not paired:
        return {
            "passed": False, "pairs": 0, "reason": "NO_PAIRED_PLACEBO_CONTROL",
            "candidate_expectancy_r": None, "placebo_expectancy_r": None,
            "delta_expectancy_r": None, "delta_lower_bound_r": None,
        }
    candidate = [float(row["shadow_r"]) for row in paired]
    placebo = [float(row["placebo_r"]) for row in paired]
    delta = [left - right for left, right in zip(candidate, placebo)]
    lower = bootstrap_lower_mean(delta, confidence=confidence)
    passed = mean(candidate) >= mean(placebo) + 0.05 and lower > 0
    return {
        "passed": passed, "pairs": len(paired),
        "reason": "BEATS_UNCONDITIONAL_NEXT_BAR" if passed else "DOES_NOT_BEAT_PLACEBO",
        "candidate_expectancy_r": mean(candidate), "placebo_expectancy_r": mean(placebo),
        "delta_expectancy_r": mean(delta), "delta_lower_bound_r": lower,
    }


def parameter_plateau_check(candidate_code: str, metrics_by_code: dict[str, dict], *,
                            tolerance_r: float = 0.20) -> dict:
    """Reject isolated optima; require support from adjacent risk geometry."""
    current = metrics_by_code.get(candidate_code) or {}
    current_expectancy = current.get("shadow_oos_r")
    if current_expectancy is None:
        return {"passed": False, "neighbors": 0, "supporting_neighbors": [],
                "reason": "NO_OOS_EXPECTANCY_FOR_PLATEAU"}
    prefix = candidate_code.split("_S", 1)[0]
    ordered = sorted(
        ((code, values) for code, values in metrics_by_code.items()
         if code.startswith(prefix + "_S") and values.get("shadow_oos_r") is not None),
        key=lambda item: float(item[1].get("stop_atr") or 0.0),
    )
    index = next((idx for idx, item in enumerate(ordered) if item[0] == candidate_code), None)
    if index is None:
        return {"passed": False, "neighbors": 0, "supporting_neighbors": [],
                "reason": "CANDIDATE_NOT_IN_PARAMETER_FAMILY"}
    neighbors = ordered[max(0, index - 1):index] + ordered[index + 1:index + 2]
    supporting = [code for code, values in neighbors
                  if float(values["shadow_oos_r"]) > 0
                  and abs(float(values["shadow_oos_r"]) - float(current_expectancy)) <= tolerance_r]
    return {
        "passed": bool(supporting), "neighbors": len(neighbors),
        "supporting_neighbors": supporting,
        "reason": "ADJACENT_PARAMETERS_SUPPORT_EDGE" if supporting else "ISOLATED_PARAMETER_PEAK",
        "tolerance_r": tolerance_r,
    }


def adaptive_shadow_gate(rows: list[dict]) -> dict:
    """Choose an auditable evidence gate from signal frequency and diversity."""
    entered = [row for row in rows if row.get("shadow_r") is not None]
    dates = sorted({str(row.get("trade_date")) for row in entered if row.get("trade_date")})
    regimes = {str(row.get("regime")) for row in entered
               if row.get("regime") and str(row.get("regime")).upper() != "UNKNOWN"}
    span_days = 0
    if dates:
        from datetime import date
        span_days = (date.fromisoformat(dates[-1]) - date.fromisoformat(dates[0])).days + 1
    active_days = len(dates)
    frequency = len(entered) / max(active_days, 1)
    # Intraday default: 60/15 across at least five active days and two regimes.
    # A long-observed stream may enter Challenger at 40/10, but still needs the
    # separate 30/10 forward phase before it can become Champion.
    early_qualified = active_days >= 10 and span_days >= 14 and len(regimes) >= 3
    min_pairs, min_oos = (40, 10) if early_qualified else (60, 15)
    gate_name = "DIVERSE_40_10_CHALLENGER" if early_qualified else "INTRADAY_60_15"
    high_confidence = len(entered) >= 120 and active_days >= 10 and len(regimes) >= 3
    confidence = "HIGH" if high_confidence else (
        "STANDARD" if len(entered) >= min_pairs else "EARLY" if len(entered) >= 40 else "ACCUMULATING")
    return {
        "min_pairs": min_pairs, "min_oos": min_oos, "gate": gate_name,
        "pairs": len(entered), "active_days": active_days, "span_days": span_days,
        "regimes": len(regimes), "signals_per_active_day": frequency, "confidence": confidence,
        "early_evidence_pairs": 40, "early_evidence_oos": 10,
    }


def evaluate_walk_forward(rows: list[dict], *, min_pairs: int | None = None,
                          min_oos: int | None = None,
                          oos_rows: list[dict] | None = None) -> dict:
    """Rank only by the chronological OOS tail and apply promotion guards."""
    entered = [row for row in rows if row.get("shadow_r") is not None]
    gate = adaptive_shadow_gate(entered)
    preliminary_placebo = negative_control_check(entered, confidence=0.95)
    preliminary_placebo["provisional"] = True
    min_pairs = int(min_pairs if min_pairs is not None else gate["min_pairs"])
    min_oos = int(min_oos if min_oos is not None else gate["min_oos"])
    if len(entered) < min_pairs:
        early = len(entered) >= 40
        provisional_oos = (len([row for row in (oos_rows or [])
                                if row.get("shadow_r") is not None])
                           if oos_rows is not None else min(min_oos, len(entered) // 4))
        return {"status": "SHADOW_EARLY_EVIDENCE" if early else "SHADOW_ACCUMULATION",
                "pairs": len(entered), "oos_pairs": provisional_oos,
                "oos_provisional": True,
                "reason": f"requires paired trades>={min_pairs}", "adaptive_gate": gate,
                "negative_control": preliminary_placebo}
    if oos_rows is None:
        oos_size = max(min_oos, len(entered) // 5)
        oos = entered[-oos_size:]
    else:
        oos = [row for row in oos_rows if row.get("shadow_r") is not None]
        oos_size = len(oos)
        if oos_size < min_oos:
            return {"status": "SHADOW_ACCUMULATION", "pairs": len(entered),
                    "oos_pairs": oos_size, "oos_provisional": True,
                    "reason": f"requires purged OOS trades>={min_oos}",
                    "adaptive_gate": gate, "negative_control": preliminary_placebo}
    actual = [float(row["actual_r"]) for row in entered]
    shadow = [float(row["shadow_r"]) for row in entered]
    actual_oos = [float(row["actual_r"]) for row in oos]
    shadow_oos = [float(row["shadow_r"]) for row in oos]
    paired_delta = [float(row["shadow_r"]) - float(row["actual_r"]) for row in entered]
    # 12 bounded variants are evaluated per state.  A 99.6% lower bound is a
    # conservative family-wise guard (approximately Bonferroni 5% / 12).
    delta_lower_bound = bootstrap_lower_mean(paired_delta, confidence=0.996)
    regime_ok, regime_counts = regime_sample_check(entered, minimum=5)
    placebo = negative_control_check(oos, confidence=0.95)
    coverage = len(entered) / max(len(rows), 1)
    wins = sorted((value for value in shadow if value > 0), reverse=True)
    concentration = wins[0] / sum(wins) if wins and sum(wins) else 1.0
    checks = {
        "expectancy_gain": mean(shadow) >= mean(actual) + 0.10,
        "shadow_expectancy_positive": mean(shadow) > 0,
        "drawdown_not_worse": max_drawdown_r(shadow) <= max_drawdown_r(actual),
        "oos_positive": mean(shadow_oos) > 0,
        "oos_better": mean(shadow_oos) > mean(actual_oos),
        "largest_win_concentration": concentration <= 0.35,
        "minimum_trading_days": gate["active_days"] >= (10 if gate["gate"] == "DIVERSE_40_10_CHALLENGER" else 5),
        "regime_diversity": gate["regimes"] >= (3 if gate["gate"] == "DIVERSE_40_10_CHALLENGER" else 2),
        "paired_delta_familywise_lower_bound_positive": delta_lower_bound > 0,
        "minimum_per_regime": regime_ok,
        "candidate_signal_coverage": coverage >= 0.50,
        "beats_unconditional_entry_placebo": placebo["passed"],
    }
    return {
        "status": "READY_FOR_PAPER_CONFIRMATION" if all(checks.values()) else "KEEP_SHADOW",
        "pairs": len(entered), "oos_pairs": oos_size,
        "actual_expectancy_r": mean(actual), "shadow_expectancy_r": mean(shadow),
        "actual_oos_r": mean(actual_oos), "shadow_oos_r": mean(shadow_oos),
        "actual_drawdown_r": max_drawdown_r(actual),
        "shadow_drawdown_r": max_drawdown_r(shadow),
        "largest_win_concentration": concentration, "checks": checks, "adaptive_gate": gate,
        "paired_delta_lower_995_r": delta_lower_bound,
        "regime_counts": regime_counts, "signal_coverage": coverage,
        "negative_control": placebo,
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
    paired_delta = [s - a for s, a in zip(shadow, actual)]
    delta_lower_bound = bootstrap_lower_mean(paired_delta, confidence=0.95)
    regime_ok, regime_counts = regime_sample_check(entered, minimum=5)
    coverage = len(entered) / max(len(rows), 1)
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
        "paired_delta_lower_bound_positive": delta_lower_bound > 0,
        "minimum_per_regime": regime_ok,
        "candidate_signal_coverage": coverage >= 0.50,
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
        "paired_delta_lower_95_r": delta_lower_bound,
        "regime_counts": regime_counts, "signal_coverage": coverage,
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
