from __future__ import annotations

import json
import math
import os
import statistics
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = Path(os.getenv("INTERMARKET_LEAD_LAG_CONFIG", ROOT / "config/research/intermarket_lead_lag_v1.json"))
SOURCE_VERSION = "INTERMARKET_LEAD_LAG_ENGINE_V1"


@dataclass(frozen=True)
class Point:
    ts: Any
    source_close: float
    target_close: float
    regime: str
    regime_confidence: float


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * q)))
    return ordered[index]


def regime_group(regime: str) -> str:
    value = (regime or "").lower()
    if value.startswith("trend_") and "expansion" not in value:
        return "TREND"
    if value.startswith("range_"):
        return "RANGE"
    if "expansion" in value:
        return "EXPANSION"
    if "compression" in value:
        return "COMPRESSION"
    return "UNKNOWN"


def load_prices(cur, symbol: str, timeframe: str) -> dict[Any, float]:
    if symbol == "BR_ROLLING@RTSX":
        cur.execute("SELECT ts,close FROM public.market_bars_br_m5_rolling_v1 WHERE close IS NOT NULL ORDER BY ts")
    else:
        cur.execute("SELECT ts,close FROM public.market_bars WHERE symbol=%s AND timeframe=%s AND close IS NOT NULL ORDER BY ts", (symbol, timeframe))
    return {row["ts"]: float(row["close"]) for row in cur.fetchall() if float(row["close"]) > 0}


def load_points(cur, source: str, target: str, timeframe: str, min_confidence: float) -> tuple[list[Point], float]:
    source_prices = load_prices(cur, source, timeframe)
    target_prices = load_prices(cur, target, timeframe)
    timestamps = sorted(set(source_prices).intersection(target_prices))
    cur.execute("""
        SELECT DISTINCT ON (ts) ts,regime,confidence
        FROM analytics_regime_snapshots_v2
        WHERE symbol=%s AND timeframe=%s AND confidence >= %s
        ORDER BY ts,confidence DESC,updated_at DESC
    """, (target, timeframe, min_confidence))
    regimes = {row["ts"]: (str(row["regime"]), float(row["confidence"])) for row in cur.fetchall()}
    covered = sum(1 for ts in timestamps if ts in regimes)
    points = [Point(ts, source_prices[ts], target_prices[ts], regimes.get(ts, ("UNKNOWN", 0.0))[0], regimes.get(ts, ("UNKNOWN", 0.0))[1]) for ts in timestamps]
    return points, covered / len(points) if points else 0.0


def sample_rows(points: list[Point], impulse: int, lag: int, threshold: float, selected_regime: str, cost_bps: float, direction: int) -> list[dict[str, Any]]:
    rows = []
    i = impulse
    while i + lag < len(points):
        source_return = points[i].source_close / points[i - impulse].source_close - 1.0
        group = regime_group(points[i].regime)
        if abs(source_return) < threshold or (selected_regime != "ALL" and group != selected_regime):
            i += 1
            continue
        target_return = points[i + lag].target_close / points[i].target_close - 1.0
        predicted_side = direction * (1 if source_return > 0 else -1)
        pnl_bps = predicted_side * target_return * 10000.0 - cost_bps
        rows.append({"index": i, "ts": points[i].ts, "signal": source_return * direction, "target": target_return, "pnl": pnl_bps})
        i += lag
    return rows


def metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
    pnls = [row["pnl"] for row in rows]
    wins = [value for value in pnls if value > 0]
    losses = [value for value in pnls if value <= 0]
    gross_loss = abs(sum(losses))
    equity = peak = max_drawdown = 0.0
    for value in pnls:
        equity += value
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity - peak)
    expectancy = statistics.fmean(pnls) if pnls else 0.0
    stdev = statistics.pstdev(pnls) if len(pnls) > 1 else 0.0
    t_stat = expectancy / (stdev / math.sqrt(len(pnls))) if stdev > 0 else 0.0
    raw_p = 0.5 * math.erfc(t_stat / math.sqrt(2.0)) if t_stat > 0 else 1.0
    return {
        "trades": len(pnls),
        "profit_factor": sum(wins) / gross_loss if gross_loss else (sum(wins) if wins else 0.0),
        "expectancy": expectancy,
        "hit_rate": len(wins) / len(pnls) if pnls else 0.0,
        "max_drawdown": max_drawdown,
        "raw_p": raw_p,
    }


def correlation(rows: list[dict[str, Any]]) -> float:
    if len(rows) < 3:
        return 0.0
    xs = [row["signal"] for row in rows]
    ys = [row["target"] for row in rows]
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    numerator = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    denominator = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return numerator / denominator if denominator else 0.0


def fold_passes(rows: list[dict[str, Any]], start: int, end: int) -> int:
    span = max(1, (end - start) // 3)
    passed = 0
    for fold in range(3):
        left = start + fold * span
        right = end if fold == 2 else min(end, left + span)
        item = metrics([row for row in rows if left <= row["index"] < right])
        passed += int(item["trades"] >= 8 and item["profit_factor"] >= 1.0 and item["expectancy"] > 0)
    return passed


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    run_id = uuid.uuid4()
    candidates: list[dict[str, Any]] = []
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for relation in config["relationships"]:
                points, coverage = load_points(cur, relation["source"], relation["target"], config["timeframe"], float(config["minimum_regime_confidence"]))
                if len(points) < 400:
                    continue
                train_end = int(len(points) * 0.50)
                validation_end = int(len(points) * 0.75)
                for impulse in config["impulse_bars"]:
                    train_impulses = [abs(points[i].source_close / points[i - impulse].source_close - 1.0) for i in range(impulse, train_end)]
                    threshold = percentile(train_impulses, float(config["signal_quantile"]))
                    for lag in config["lag_bars"]:
                        for selected_regime in config["regime_groups"]:
                            rows = sample_rows(points, impulse, lag, threshold, selected_regime, float(relation["cost_bps"]), int(relation["direction"]))
                            validation_rows = [row for row in rows if train_end <= row["index"] < validation_end]
                            oos_rows = [row for row in rows if validation_end <= row["index"] < len(points)]
                            validation = metrics(validation_rows)
                            oos = metrics(oos_rows)
                            candidates.append({
                                "relation": relation, "impulse": impulse, "lag": lag, "regime": selected_regime,
                                "threshold": threshold, "aligned": len(points), "coverage": coverage,
                                "validation": validation, "oos": oos, "ic": correlation(oos_rows),
                                "folds": fold_passes(oos_rows, validation_end, len(points)),
                            })

            total_trials = len(candidates)
            for trial_number, item in enumerate(candidates, start=1):
                relation, validation, oos = item["relation"], item["validation"], item["oos"]
                adjusted_p = min(1.0, oos["raw_p"] * total_trials)
                verified = item["coverage"] >= float(config["minimum_regime_coverage"])
                passed = (
                    verified and validation["trades"] >= 30 and validation["profit_factor"] >= 1.05 and validation["expectancy"] > 0
                    and oos["trades"] >= 30 and oos["profit_factor"] >= 1.15 and oos["expectancy"] > 0
                    and item["folds"] >= 2 and adjusted_p <= 0.05
                )
                verdict = "OOS_PASS" if passed else ("OOS_FAIL" if verified else "UNVERIFIED")
                reason = "PASS" if passed else ("INSUFFICIENT_REGIME_COVERAGE" if not verified else "LEAD_LAG_OOS_GATE_FAILED")
                score = min(100.0, max(0.0, (oos["profit_factor"] - 1.0) * 35.0) + max(0.0, oos["expectancy"]) * 2.0 + item["folds"] * 8.0 + max(0.0, item["ic"]) * 20.0)
                cur.execute("""
                    INSERT INTO analytics.intermarket_lead_lag_result_v1 (
                        discovery_run_id,trial_number,total_trials,relationship_code,thesis,source_symbol,target_symbol,timeframe,
                        impulse_bars,lag_bars,expected_direction,regime_group,signal_threshold,aligned_bars,regime_coverage_ratio,
                        validation_trades,validation_profit_factor,validation_expectancy_bps,oos_trades,oos_profit_factor,
                        oos_expectancy_bps,oos_hit_rate,oos_information_coefficient,oos_max_drawdown_bps,folds_passed,folds_total,
                        raw_p_value,adjusted_p_value,hypothesis_score,trust_status,verdict_code,reason_code,promotion_allowed,
                        catalog_version,source_version
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,3,%s,%s,%s,%s,%s,%s,false,%s,%s)
                """, (str(run_id),trial_number,total_trials,relation["code"],relation["thesis"],relation["source"],relation["target"],config["timeframe"],
                      item["impulse"],item["lag"],relation["direction"],item["regime"],item["threshold"],item["aligned"],item["coverage"],
                      validation["trades"],validation["profit_factor"],validation["expectancy"],oos["trades"],oos["profit_factor"],
                      oos["expectancy"],oos["hit_rate"],item["ic"],oos["max_drawdown"],item["folds"],oos["raw_p"],adjusted_p,score,
                      "VERIFIED" if verified else "UNVERIFIED",verdict,reason,config["catalog_version"],SOURCE_VERSION))

    ranked = sorted(candidates, key=lambda item: (item["oos"]["profit_factor"], item["oos"]["expectancy"]), reverse=True)
    print(f"discovery_run_id={run_id}")
    print(f"relationships={len(config['relationships'])}")
    print(f"total_trials={len(candidates)}")
    print("promotion_allowed=0")
    print("VERDICT=INTERMARKET_LEAD_LAG_ENGINE_V1_READY")


if __name__ == "__main__":
    main()
