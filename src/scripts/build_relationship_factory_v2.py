from __future__ import annotations

import json
import math
import os
import statistics
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = Path(os.getenv("RELATIONSHIP_FACTORY_CONFIG", ROOT / "config/research/relationship_factory_v2.json"))
SOURCE_VERSION = "RELATIONSHIP_FACTORY_ENGINE_V2"


@dataclass(frozen=True)
class Point:
    ts: Any
    source_index: float
    target_close: float
    regime: str


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, max(0, int((len(ordered) - 1) * q)))]


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


def session_code(ts: Any, timezone: str) -> str:
    local = ts.astimezone(ZoneInfo(timezone))
    minute = local.hour * 60 + local.minute
    if 600 <= minute < 630:
        return "MOEX_OPEN"
    if 630 <= minute < 660:
        return "MOEX_FIRST_HOUR"
    if 660 <= minute < 990:
        return "EUROPE_OVERLAP"
    if 990 <= minute < 1080:
        return "US_OPEN"
    if 1080 <= minute < 1420:
        return "EVENING"
    if 1420 <= minute < 1430:
        return "MOEX_CLOSE"
    return "OUTSIDE_SESSION"


def load_prices(cur, symbol: str, timeframe: str) -> dict[Any, float]:
    if symbol == "BR_ROLLING@RTSX":
        cur.execute("SELECT ts,close FROM public.market_bars_br_m5_rolling_v1 WHERE close>0 ORDER BY ts")
    else:
        cur.execute("SELECT ts,close FROM public.market_bars WHERE symbol=%s AND timeframe=%s AND close>0 ORDER BY ts", (symbol, timeframe))
    return {row["ts"]: float(row["close"]) for row in cur.fetchall()}


def load_points(cur, relation: dict[str, Any], config: dict[str, Any]) -> tuple[list[Point], float]:
    sources = [load_prices(cur, symbol, config["timeframe"]) for symbol in relation["sources"]]
    target = load_prices(cur, relation["target"], config["timeframe"])
    timestamps = set(target)
    for source in sources:
        timestamps.intersection_update(source)
    ordered = sorted(timestamps)
    if not ordered:
        return [], 0.0
    source_index: dict[Any, float] = {ordered[0]: 100.0}
    for previous, current in zip(ordered, ordered[1:]):
        returns = [source[current] / source[previous] - 1.0 for source in sources if source.get(previous, 0) > 0]
        if len(returns) != len(sources):
            continue
        combined = returns[0] if relation["construction"] == "SINGLE_RETURN" else statistics.fmean(returns)
        source_index[current] = source_index.get(previous, 100.0) * (1.0 + combined)
    cur.execute("""
        SELECT DISTINCT ON (ts) ts,regime FROM analytics_regime_snapshots_v2
        WHERE symbol=%s AND timeframe=%s AND confidence >= %s
        ORDER BY ts,confidence DESC,updated_at DESC
    """, (relation["target"], config["timeframe"], config["minimum_regime_confidence"]))
    regimes = {row["ts"]: str(row["regime"]) for row in cur.fetchall()}
    usable = [ts for ts in ordered if ts in source_index]
    coverage = sum(ts in regimes for ts in usable) / len(usable) if usable else 0.0
    return [Point(ts, source_index[ts], target[ts], regimes.get(ts, "UNKNOWN")) for ts in usable], coverage


def sample(points: list[Point], impulse: int, lag: int, threshold: float, selected_regime: str,
           selected_session: str, timezone: str, cost_bps: float, direction: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    i = impulse
    while i + lag < len(points):
        signal = points[i].source_index / points[i - impulse].source_index - 1.0
        group = regime_group(points[i].regime)
        session = session_code(points[i].ts, timezone)
        if abs(signal) < threshold or (selected_regime != "ALL" and group != selected_regime) or (selected_session != "ALL" and session != selected_session):
            i += 1
            continue
        target_return = points[i + lag].target_close / points[i].target_close - 1.0
        side = direction * (1 if signal > 0 else -1)
        rows.append({"index": i, "pnl": side * target_return * 10000.0 - cost_bps})
        i += lag
    return rows


def metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
    values = [row["pnl"] for row in rows]
    wins, losses = [v for v in values if v > 0], [v for v in values if v <= 0]
    gross_loss = abs(sum(losses))
    equity = peak = drawdown = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = min(drawdown, equity - peak)
    expectancy = statistics.fmean(values) if values else 0.0
    stdev = statistics.pstdev(values) if len(values) > 1 else 0.0
    t_stat = expectancy / (stdev / math.sqrt(len(values))) if expectancy > 0 and stdev > 0 else 0.0
    return {"trades": len(values), "profit_factor": sum(wins) / gross_loss if gross_loss else (sum(wins) if wins else 0.0),
            "expectancy": expectancy, "hit_rate": len(wins) / len(values) if values else 0.0, "drawdown": drawdown,
            "raw_p": 0.5 * math.erfc(t_stat / math.sqrt(2.0)) if t_stat > 0 else 1.0}


def folds(rows: list[dict[str, Any]], start: int, end: int) -> int:
    span = max(1, (end - start) // 3)
    passed = 0
    for fold in range(3):
        left, right = start + fold * span, end if fold == 2 else start + (fold + 1) * span
        item = metrics([row for row in rows if left <= row["index"] < right])
        passed += int(item["trades"] >= 6 and item["profit_factor"] >= 1.0 and item["expectancy"] > 0)
    return passed


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    run_id = uuid.uuid4()
    candidates: list[dict[str, Any]] = []
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for relation in sorted(config["relationships"], key=lambda item: (item["priority"], item["code"])):
                points, coverage = load_points(cur, relation, config)
                if len(points) < 100:
                    continue
                train_end, validation_end = int(len(points) * 0.50), int(len(points) * 0.75)
                for impulse in config["impulse_bars"]:
                    train_signals = [abs(points[i].source_index / points[i - impulse].source_index - 1.0) for i in range(impulse, train_end)]
                    threshold = percentile(train_signals, config["signal_quantile"])
                    for lag in config["lag_bars"]:
                        for regime in config["regime_groups"]:
                            for session in config["session_groups"]:
                                rows = sample(points, impulse, lag, threshold, regime, session, config["timezone"], relation["cost_bps"], relation["direction"])
                                validation_rows = [row for row in rows if train_end <= row["index"] < validation_end]
                                oos_rows = [row for row in rows if validation_end <= row["index"] < len(points)]
                                candidates.append({"relation": relation, "impulse": impulse, "lag": lag, "regime": regime,
                                    "session": session, "threshold": threshold, "aligned": len(points), "coverage": coverage,
                                    "validation": metrics(validation_rows), "oos": metrics(oos_rows),
                                    "folds": folds(oos_rows, validation_end, len(points))})
            total_trials = len(candidates)
            for item in candidates:
                relation, validation, oos = item["relation"], item["validation"], item["oos"]
                adjusted_p = min(1.0, oos["raw_p"] * total_trials)
                verified = item["aligned"] >= config["minimum_aligned_bars"] and item["coverage"] >= config["minimum_regime_coverage"]
                passed = verified and validation["trades"] >= config["minimum_validation_trades"] and validation["profit_factor"] >= 1.05 and validation["expectancy"] > 0 and oos["trades"] >= config["minimum_oos_trades"] and oos["profit_factor"] >= 1.15 and oos["expectancy"] > 0 and item["folds"] >= 2 and adjusted_p <= 0.05
                verdict = "OOS_PASS" if passed else ("OOS_FAIL" if verified else "UNVERIFIED")
                reason = "PASS" if passed else ("INSUFFICIENT_ALIGNED_HISTORY" if item["aligned"] < config["minimum_aligned_bars"] else ("INSUFFICIENT_REGIME_COVERAGE" if not verified else "RELATIONSHIP_OOS_GATE_FAILED"))
                cur.execute("""INSERT INTO analytics.relationship_factory_result_v2
                    (discovery_run_id,catalog_version,priority,relationship_family,relationship_code,thesis,source_symbols,
                     source_construction,target_symbol,timeframe,impulse_bars,lag_bars,regime_group,session_code,signal_threshold,
                     aligned_bars,regime_coverage_ratio,validation_trades,validation_profit_factor,validation_expectancy_bps,
                     oos_trades,oos_profit_factor,oos_expectancy_bps,oos_hit_rate,oos_max_drawdown_bps,folds_passed,folds_total,
                     raw_p_value,adjusted_p_value,trust_status,verdict_code,reason_code,promotion_allowed,source_version)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,3,%s,%s,%s,%s,%s,false,%s)""",
                    (str(run_id),config["catalog_version"],relation["priority"],relation["family"],relation["code"],relation["thesis"],
                     psycopg2.extras.Json(relation["sources"]),relation["construction"],relation["target"],config["timeframe"],item["impulse"],
                     item["lag"],item["regime"],item["session"],item["threshold"],item["aligned"],item["coverage"],validation["trades"],
                     validation["profit_factor"],validation["expectancy"],oos["trades"],oos["profit_factor"],oos["expectancy"],oos["hit_rate"],
                     oos["drawdown"],item["folds"],oos["raw_p"],adjusted_p,"VERIFIED" if verified else "UNVERIFIED",verdict,reason,SOURCE_VERSION))
    print(f"discovery_run_id={run_id}")
    print(f"relationships={len(config['relationships'])}")
    print(f"total_trials={len(candidates)}")
    print("promotion_allowed=0")
    print("VERDICT=RELATIONSHIP_FACTORY_V2_READY")


if __name__ == "__main__":
    main()
