from __future__ import annotations

import json
import math
import os
import statistics
import uuid
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras

from scripts.build_edge_hypothesis_discovery_v1 import load_search_configuration
from scripts.build_strategy_execution_runner_v1 import Bar, Trade, build_trades, metrics


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = Path(os.getenv("SESSION_EXECUTION_EDGE_CONFIG", ROOT / "config/research/session_execution_edge_v1.json"))
SOURCE_VERSION = "SESSION_EXECUTION_EDGE_ENGINE_V2_MICROSTRUCTURE_COHORT"
MIN_BARS = int(os.getenv("SESSION_EDGE_MIN_BARS", "6000"))
MAX_MARKETS = int(os.getenv("SESSION_EDGE_MAX_MARKETS", "12"))
MIN_MICROSTRUCTURE_COVERAGE = float(os.getenv("MICROSTRUCTURE_MIN_COVERAGE", "0.80"))
MAX_QUOTE_DISTANCE_SECONDS = int(os.getenv("MICROSTRUCTURE_MAX_QUOTE_DISTANCE_SECONDS", "5"))
MIN_FRESH_MICROSTRUCTURE_SYMBOLS = int(os.getenv("MICROSTRUCTURE_MIN_FRESH_SYMBOLS", "2"))
MIN_FRESH_SNAPSHOTS_PER_SYMBOL = int(os.getenv("MICROSTRUCTURE_MIN_FRESH_SNAPSHOTS", "30"))
FRESH_WINDOW_MINUTES = int(os.getenv("MICROSTRUCTURE_FRESH_WINDOW_MINUTES", "15"))

ALLOWED_REGIMES = {
    "MOMENTUM": ("trend_up", "trend_down", "trend_up_expansion", "trend_down_expansion"),
    "MEAN_REVERSION": ("range_normal", "range_compression", "compression"),
    "BREAKOUT": ("compression", "trend_up_expansion", "trend_down_expansion"),
}


def normalized_symbol(symbol: str) -> str:
    value = str(symbol or "").upper()
    match = re.match(r"^([A-Z]+)[FGHJKMNQUVXZ][0-9]*@RTSX$", value)
    return f"{match.group(1)}_CONT" if match else value


def minute_of_day(value: str) -> int:
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


def session_for(ts: Any, config: dict[str, Any]) -> str:
    local = ts.astimezone(ZoneInfo(config["timezone"]))
    minute = local.hour * 60 + local.minute
    for session in config["sessions"]:
        if minute_of_day(session["start"]) <= minute < minute_of_day(session["end"]):
            return session["code"]
    return "OUTSIDE_SESSION"


def one_sided_p(values: list[float]) -> float:
    if len(values) < 3:
        return 1.0
    mean = statistics.fmean(values)
    stdev = statistics.pstdev(values)
    if mean <= 0 or stdev <= 0:
        return 1.0
    return 0.5 * math.erfc((mean / (stdev / math.sqrt(len(values)))) / math.sqrt(2.0))


def fold_passes(trades: list[Trade], bars: list[Bar], start: int) -> int:
    span = max(1, (len(bars) - start) // 3)
    passed = 0
    for fold in range(3):
        left = bars[start + fold * span].ts
        right_index = len(bars) - 1 if fold == 2 else min(len(bars) - 1, start + (fold + 1) * span)
        right = bars[right_index].ts
        item = metrics([trade for trade in trades if left <= trade.entry_ts <= right])
        passed += int(item["trades"] >= 6 and item["profit_factor"] >= 1.0 and item["expectancy"] > 0)
    return passed


def trade_fold_passes(trades: list[Trade]) -> int:
    """Evaluate only the independently quote-matched execution cohort."""
    ordered = sorted(trades, key=lambda trade: trade.entry_ts)
    if not ordered:
        return 0
    passed = 0
    for fold in range(3):
        left = len(ordered) * fold // 3
        right = len(ordered) * (fold + 1) // 3
        item = metrics(ordered[left:right])
        passed += int(item["trades"] >= 6 and item["profit_factor"] >= 1.0 and item["expectancy"] > 0)
    return passed


@dataclass(frozen=True)
class VerifiedQuote:
    bid: float
    ask: float
    bid_levels: int
    ask_levels: int
    exchange_ts: Any


def fresh_microstructure_symbols(cur: Any) -> int:
    """Return symbols with enough recent, executable order-book evidence."""
    cur.execute(
        """
        SELECT count(*) AS ready_symbols
        FROM (
            SELECT symbol
            FROM analytics.market_microstructure_snapshot_v1
            WHERE observed_at >= now()-(%s * interval '1 minute')
              AND best_bid > 0 AND best_ask > best_bid
              AND bid_levels > 0 AND ask_levels > 0
              AND bid_depth > 0 AND ask_depth > 0
            GROUP BY symbol
            HAVING count(*) >= %s
        ) ready
        """,
        (FRESH_WINDOW_MINUTES, MIN_FRESH_SNAPSHOTS_PER_SYMBOL),
    )
    row = cur.fetchone()
    return int((row or {}).get("ready_symbols") or 0)


def load_verified_quotes(
    cur: Any, symbol: str, timestamps: list[Any], cache: dict[Any, VerifiedQuote | None]
) -> None:
    """Match every trade boundary to a real, sufficiently deep exchange quote."""
    missing = sorted({timestamp for timestamp in timestamps if timestamp not in cache})
    for offset in range(0, len(missing), 500):
        chunk = missing[offset:offset + 500]
        cur.execute(
            """
            WITH events AS (
                SELECT unnest(%s::timestamptz[]) AS event_ts
            )
            SELECT events.event_ts, quote.best_bid, quote.best_ask,
                   quote.bid_levels, quote.ask_levels, quote.quote_ts
            FROM events
            LEFT JOIN LATERAL (
                SELECT best_bid, best_ask, bid_levels, ask_levels,
                       coalesce(exchange_ts, observed_at) AS quote_ts
                FROM analytics.market_microstructure_snapshot_v1
                WHERE symbol=%s
                  AND observed_at BETWEEN events.event_ts - (%s * interval '1 second')
                                      AND events.event_ts + (%s * interval '1 second')
                  AND best_bid > 0 AND best_ask > best_bid
                  AND bid_levels > 0 AND ask_levels > 0
                  AND bid_depth > 0 AND ask_depth > 0
                  AND abs(extract(epoch FROM
                      (coalesce(exchange_ts, observed_at) - events.event_ts))) <= %s
                ORDER BY abs(extract(epoch FROM
                         (coalesce(exchange_ts, observed_at) - events.event_ts))),
                         snapshot_id DESC
                LIMIT 1
            ) quote ON true
            """,
            (chunk, symbol, MAX_QUOTE_DISTANCE_SECONDS,
             MAX_QUOTE_DISTANCE_SECONDS, MAX_QUOTE_DISTANCE_SECONDS),
        )
        for row in cur.fetchall():
            if row["best_bid"] is None:
                cache[row["event_ts"]] = None
            else:
                cache[row["event_ts"]] = VerifiedQuote(
                    bid=float(row["best_bid"]), ask=float(row["best_ask"]),
                    bid_levels=int(row["bid_levels"]), ask_levels=int(row["ask_levels"]),
                    exchange_ts=row["quote_ts"],
                )


def apply_microstructure_execution(
    trades: list[Trade], quotes: dict[Any, VerifiedQuote | None]
) -> list[Trade]:
    """Price BUY at ask/bid and SELL at bid/ask; reject unmatched trades."""
    verified: list[Trade] = []
    for trade in trades:
        entry = quotes.get(trade.entry_ts)
        exit_quote = quotes.get(trade.exit_ts)
        if entry is None or exit_quote is None:
            continue
        if trade.side == "BUY":
            entry_price, exit_price, side = entry.ask, exit_quote.bid, 1
        else:
            entry_price, exit_price, side = entry.bid, exit_quote.ask, -1
        gross = (exit_price - entry_price) * side
        net = gross - trade.commission - trade.slippage
        verified.append(Trade(
            len(verified) + 1, trade.side, trade.entry_ts, trade.exit_ts,
            entry_price, exit_price, gross, trade.commission, trade.slippage, net,
            quote_source="MICROSTRUCTURE_SNAPSHOT_V1",
        ))
    return verified


def reprice(
    trades: list[Trade], bars: list[Bar], regime_by_ts: dict[Any, str], policy: dict[str, Any],
    session_by_ts: dict[Any, str], base_hold: int,
) -> list[Trade]:
    index = {bar.ts: i for i, bar in enumerate(bars)}
    result: list[Trade] = []
    for trade in trades:
        entry_index = index.get(trade.entry_ts)
        if entry_index is None:
            continue
        if policy["kind"] == "SESSION_FILTER" and session_by_ts.get(trade.entry_ts) in policy.get("excluded_sessions", []):
            continue
        hold = max(1, round(base_hold * float(policy.get("hold_multiplier", 1.0))))
        exit_index = min(len(bars) - 1, entry_index + hold)
        if policy["kind"] == "REGIME_CHANGE_EXIT":
            entry_regime = regime_by_ts.get(trade.entry_ts)
            for candidate in range(entry_index + 1, exit_index + 1):
                candidate_regime = regime_by_ts.get(bars[candidate].ts)
                if entry_regime and candidate_regime and candidate_regime != entry_regime:
                    exit_index = candidate
                    break
        side = 1 if trade.side == "BUY" else -1
        exit_bar = bars[exit_index]
        gross = (exit_bar.close - trade.entry_price) * side
        net = gross - trade.commission - trade.slippage
        result.append(Trade(len(result) + 1, trade.side, trade.entry_ts, exit_bar.ts, trade.entry_price,
                            exit_bar.close, gross, trade.commission, trade.slippage, net))
    return result


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    run_id = uuid.uuid4()
    session_candidates: list[dict[str, Any]] = []
    execution_candidates: list[dict[str, Any]] = []
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""SELECT * FROM analytics.microstructure_clean_cohort_policy_v4
                           WHERE enabled""")
            clean_policies = {str(row["normalized_symbol"]): dict(row) for row in cur.fetchall()}
            ready_symbols = fresh_microstructure_symbols(cur)
            if ready_symbols < MIN_FRESH_MICROSTRUCTURE_SYMBOLS:
                print(f"fresh_microstructure_symbols={ready_symbols}")
                print("VERDICT=WAITING_FOR_FRESH_MICROSTRUCTURE")
                return
            cur.execute("""
                SELECT symbol
                FROM analytics.microstructure_research_priority_v1
                WHERE selected_for_analysis
                ORDER BY priority_rank
                LIMIT %s
            """, (MAX_MARKETS,))
            priority_symbols = [str(row["symbol"]) for row in cur.fetchall()]
            if priority_symbols:
                cur.execute("""
                    SELECT symbol,timeframe,count(*) AS bars
                    FROM public.market_bars
                    WHERE timeframe=%s AND symbol=ANY(%s)
                    GROUP BY symbol,timeframe HAVING count(*) >= %s
                    ORDER BY count(*) DESC LIMIT %s
                """, (config["timeframe"], priority_symbols, MIN_BARS, MAX_MARKETS))
            else:
                cur.execute("""
                    SELECT symbol,timeframe,count(*) AS bars FROM public.market_bars
                    WHERE timeframe=%s GROUP BY symbol,timeframe HAVING count(*) >= %s
                    ORDER BY count(*) DESC LIMIT %s
                """, (config["timeframe"], MIN_BARS, MAX_MARKETS))
            markets = cur.fetchall()
            print(f"priority_symbols={','.join(priority_symbols) or 'fallback'}")
            for market in markets:
                quote_cache: dict[Any, VerifiedQuote | None] = {}
                cur.execute("SELECT ts,close FROM public.market_bars WHERE symbol=%s AND timeframe=%s AND close IS NOT NULL ORDER BY ts",
                            (market["symbol"], market["timeframe"]))
                bars = [Bar(row["ts"], float(row["close"])) for row in cur.fetchall()]
                if len(bars) < MIN_BARS:
                    continue
                cur.execute("""
                    SELECT DISTINCT ON (ts) ts,regime,confidence FROM analytics_regime_snapshots_v2
                    WHERE symbol=%s AND timeframe=%s AND confidence >= %s
                    ORDER BY ts,confidence DESC,updated_at DESC
                """, (market["symbol"], market["timeframe"], config["minimum_regime_confidence"]))
                regime_by_ts = {row["ts"]: str(row["regime"]) for row in cur.fetchall()}
                coverage = len(set(regime_by_ts).intersection(bar.ts for bar in bars)) / len(bars)
                session_by_ts = {bar.ts: session_for(bar.ts, config) for bar in bars}
                train_end, validation_end = int(len(bars) * 0.50), int(len(bars) * 0.75)
                validation_start, oos_start = bars[train_end].ts, bars[validation_end].ts
                cost_bps = 20.0 if str(market["symbol"]).endswith("USD") else 8.0
                cost = statistics.median(bar.close for bar in bars) * cost_bps / 10000.0
                configurations = load_search_configuration(cur)
                for family, configuration in configurations:
                    targets = configuration["regime_policy"].get("target_symbols", [])
                    if targets and market["symbol"] not in targets:
                        continue
                    strategy_code, grid = configuration["strategy_code"], configuration["grid"]
                    for base_params in grid:
                        hold = int(base_params.get("hold", 5))
                        params = {**base_params, "commission": cost, "slippage": 0.0}
                        lookback = int(params["lookback"])
                        run = {"strategy_code": strategy_code, "parameter_json": params}
                        validation_all = [t for t in build_trades(run, bars[train_end - lookback:validation_end]) if t.entry_ts >= validation_start]
                        oos_all = [t for t in build_trades(run, bars[validation_end - lookback:]) if t.entry_ts >= oos_start]
                        allowed_regimes = tuple(
                            configuration["regime_policy"].get("allowed_regimes")
                            or ALLOWED_REGIMES.get(family)
                            or ALLOWED_REGIMES["MOMENTUM"]
                        )
                        for regime in allowed_regimes:
                            for session in [item["code"] for item in config["sessions"]]:
                                validation = [t for t in validation_all if regime_by_ts.get(t.entry_ts) == regime and session_by_ts.get(t.entry_ts) == session]
                                oos = [t for t in oos_all if regime_by_ts.get(t.entry_ts) == regime and session_by_ts.get(t.entry_ts) == session]
                                vm, om = metrics(validation), metrics(oos)
                                session_candidates.append({"family": family, "strategy": strategy_code, "market": market,
                                    "params": base_params, "regime": regime, "session": session, "coverage": coverage,
                                    "validation": vm, "oos": om, "folds": fold_passes(oos, bars, validation_end),
                                    "raw_p": one_sided_p([t.net_pnl for t in oos])})
                                for policy in config["execution_policies"]:
                                    repriced = reprice(oos, bars, regime_by_ts, policy, session_by_ts, hold)
                                    clean_policy = clean_policies.get(normalized_symbol(str(market["symbol"])))
                                    cohort_code = "MICROSTRUCTURE_ONLY"
                                    if clean_policy is not None:
                                        cohort_start = clean_policy["cohort_started_at"]
                                        repriced = [trade for trade in repriced
                                                    if trade.entry_ts >= cohort_start and trade.exit_ts >= cohort_start]
                                        cohort_code = "MICROSTRUCTURE_CLEAN_V4"
                                    boundaries = [timestamp for trade in repriced for timestamp in (trade.entry_ts, trade.exit_ts)]
                                    load_verified_quotes(cur, str(market["symbol"]), boundaries, quote_cache)
                                    verified_trades = apply_microstructure_execution(repriced, quote_cache)
                                    eligible = len(repriced)
                                    matched = len(verified_trades)
                                    if matched == 0:
                                        continue
                                    microstructure_coverage = matched / eligible if eligible else 0.0
                                    item_metrics = metrics(verified_trades)
                                    baseline_repriced = reprice(oos, bars, regime_by_ts,
                                                                {"kind": "BASELINE", "hold_multiplier": 1.0},
                                                                session_by_ts, hold)
                                    load_verified_quotes(cur, str(market["symbol"]),
                                                         [timestamp for trade in baseline_repriced
                                                          for timestamp in (trade.entry_ts, trade.exit_ts)], quote_cache)
                                    baseline_metrics = metrics(apply_microstructure_execution(baseline_repriced, quote_cache))
                                    execution_candidates.append({"family": family, "strategy": strategy_code, "market": market,
                                        "params": base_params, "regime": regime, "session": session, "coverage": coverage,
                                        "policy": policy["code"], "oos": item_metrics, "baseline": baseline_metrics,
                                        "folds": trade_fold_passes(verified_trades),
                                        "market_data_quality": "QUOTE_MATCHED",
                                        "cohort_code": cohort_code,
                                        "required_microstructure_coverage": float(
                                            clean_policy["min_coverage_ratio"] if clean_policy else MIN_MICROSTRUCTURE_COVERAGE
                                        ),
                                        "required_matched_trades": int(
                                            clean_policy["min_matched_trades"] if clean_policy else config["minimum_oos_trades"]
                                        ),
                                        "eligible": eligible, "matched": matched,
                                        "microstructure_coverage": microstructure_coverage,
                                        "microstructure_start": min(t.entry_ts for t in verified_trades),
                                        "microstructure_end": max(t.exit_ts for t in verified_trades),
                                        "raw_p": one_sided_p([t.net_pnl for t in verified_trades])})

            session_trials = len(session_candidates)
            for item in session_candidates:
                adjusted = min(1.0, item["raw_p"] * session_trials)
                verified = item["coverage"] >= config["minimum_regime_coverage"]
                vm, om = item["validation"], item["oos"]
                passed = verified and vm["trades"] >= config["minimum_validation_trades"] and vm["profit_factor"] >= 1.05 and vm["expectancy"] > 0 and om["trades"] >= config["minimum_oos_trades"] and om["profit_factor"] >= 1.15 and om["expectancy"] > 0 and item["folds"] >= 2 and adjusted <= 0.05
                verdict = "OOS_PASS" if passed else ("OOS_FAIL" if verified else "UNVERIFIED")
                reason = "PASS" if passed else ("INSUFFICIENT_REGIME_COVERAGE" if not verified else "SESSION_OOS_GATE_FAILED")
                cur.execute("""INSERT INTO analytics.edge_session_result_v1
                    (discovery_run_id,strategy_family,strategy_code,symbol,timeframe,parameter_json,regime_code,session_code,
                     session_timezone,regime_coverage_ratio,validation_trades,validation_profit_factor,validation_expectancy,
                     oos_trades,oos_profit_factor,oos_expectancy,oos_max_drawdown,folds_passed,folds_total,raw_p_value,
                     adjusted_p_value,trust_status,verdict_code,reason_code,promotion_allowed,source_version)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,3,%s,%s,%s,%s,%s,false,%s)""",
                    (str(run_id),item["family"],item["strategy"],item["market"]["symbol"],item["market"]["timeframe"],
                     psycopg2.extras.Json(item["params"]),item["regime"],item["session"],config["timezone"],item["coverage"],
                     vm["trades"],vm["profit_factor"],vm["expectancy"],om["trades"],om["profit_factor"],om["expectancy"],
                     om["max_drawdown"],item["folds"],item["raw_p"],adjusted,"VERIFIED" if verified else "UNVERIFIED",verdict,reason,SOURCE_VERSION))

            execution_trials = len(execution_candidates)
            for item in execution_candidates:
                adjusted = min(1.0, item["raw_p"] * execution_trials)
                om, baseline = item["oos"], item["baseline"]
                delta_pf, delta_exp = om["profit_factor"] - baseline["profit_factor"], om["expectancy"] - baseline["expectancy"]
                regime_verified = item["coverage"] >= config["minimum_regime_coverage"]
                quote_verified = (
                    item["microstructure_coverage"] >= item["required_microstructure_coverage"]
                    and item["matched"] >= item["required_matched_trades"]
                )
                verified = regime_verified and quote_verified
                item["market_data_quality"] = (
                    "MICROSTRUCTURE_COHORT_VERIFIED" if verified else "QUOTE_MATCHED"
                )
                passed = verified and item["policy"] != "BASELINE" and om["trades"] >= config["minimum_oos_trades"] and om["profit_factor"] >= 1.15 and delta_pf > 0 and delta_exp > 0 and item["folds"] >= 2 and adjusted <= 0.05
                verdict = "OOS_PASS" if passed else ("OOS_FAIL" if verified else "UNVERIFIED")
                reason = "PASS" if passed else ("INSUFFICIENT_REGIME_COVERAGE" if not regime_verified else ("MICROSTRUCTURE_DATA_UNVERIFIED" if not quote_verified else "EXECUTION_OOS_GATE_FAILED"))
                cur.execute("""INSERT INTO analytics.execution_edge_result_v1
                    (discovery_run_id,strategy_family,strategy_code,symbol,timeframe,parameter_json,regime_code,session_code,
                     policy_code,oos_trades,oos_profit_factor,oos_expectancy,baseline_oos_profit_factor,baseline_oos_expectancy,
                     delta_profit_factor,delta_expectancy,folds_passed,folds_total,raw_p_value,adjusted_p_value,market_data_quality,
                     trust_status,verdict_code,reason_code,promotion_allowed,source_version,cohort_code,
                     eligible_oos_trades,microstructure_matched_trades,microstructure_coverage_ratio,
                     microstructure_start,microstructure_end)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,3,%s,%s,%s,%s,%s,%s,false,%s,
                            %s,%s,%s,%s,%s,%s)""",
                    (str(run_id),item["family"],item["strategy"],item["market"]["symbol"],item["market"]["timeframe"],
                     psycopg2.extras.Json(item["params"]),item["regime"],item["session"],item["policy"],om["trades"],
                     om["profit_factor"],om["expectancy"],baseline["profit_factor"],baseline["expectancy"],delta_pf,delta_exp,
                     item["folds"],item["raw_p"],adjusted,item["market_data_quality"],
                     "VERIFIED" if verified else "UNVERIFIED",verdict,reason,SOURCE_VERSION,item["cohort_code"],
                     item["eligible"],item["matched"],item["microstructure_coverage"],
                     item["microstructure_start"],item["microstructure_end"]))

    print(f"discovery_run_id={run_id}")
    print(f"strategy_regime_session_trials={len(session_candidates)}")
    print(f"execution_policy_trials={len(execution_candidates)}")
    print("execution_cohort=MICROSTRUCTURE_ONLY")
    print("promotion_allowed=0")
    print("VERDICT=SESSION_EXECUTION_EDGE_ENGINE_V2_MICROSTRUCTURE_READY")


if __name__ == "__main__":
    main()
