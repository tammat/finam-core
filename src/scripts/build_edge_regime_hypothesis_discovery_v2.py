from __future__ import annotations

import os
import statistics
import uuid
from collections import defaultdict

import psycopg2
import psycopg2.extras

from scripts.build_edge_hypothesis_discovery_v1 import load_search_configuration, score
from scripts.build_strategy_execution_runner_v1 import Bar, Trade, build_trades, metrics
from scripts.edge_research_universe_v1 import load_research_universe
from scripts.meta_entry_policy_v2 import apply_meta_entry_policy_v2, load_meta_entry_policy_v2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "REGIME_AWARE_EDGE_DISCOVERY_V4_CONTRACT_AWARE"
MIN_BARS = int(os.getenv("EDGE_HYPOTHESIS_MIN_BARS", "6000"))
FRESHNESS_MINUTES = int(os.getenv("EDGE_SEARCH_FRESHNESS_MINUTES", "15"))
MIN_CONFIDENCE = float(os.getenv("EDGE_REGIME_MIN_CONFIDENCE", "0.60"))
MIN_COVERAGE = float(os.getenv("EDGE_REGIME_MIN_COVERAGE", "0.80"))


def _attach_reference(cur, bars: list[Bar], symbol: str | None, timeframe: str) -> list[Bar]:
    if not symbol:
        return bars
    cur.execute("""SELECT ts,close FROM public.market_bars WHERE symbol=%s AND timeframe=%s
        AND close IS NOT NULL AND source NOT IN ('unknown','synthetic_futures_backfill_v1') ORDER BY ts""",
        (symbol,timeframe))
    reference = {row["ts"]: float(row["close"]) for row in cur.fetchall()}
    return [Bar(bar.ts,bar.close,bar.volume,reference.get(bar.ts)) for bar in bars]

def _filtered(trades: list[Trade], regime_by_ts: dict[object, str], regime: str) -> list[Trade]:
    return [trade for trade in trades if regime_by_ts.get(trade.entry_ts) == regime]


def _fold_passes(trades: list[Trade], bars: list[Bar], start_index: int, gate: dict) -> int:
    if not trades:
        return 0
    fold_span = max(1, (len(bars) - start_index) // 3)
    passed = 0
    for fold_no in range(3):
        start = start_index + fold_no * fold_span
        end = len(bars) if fold_no == 2 else min(len(bars), start + fold_span)
        fold = metrics([trade for trade in trades if bars[start].ts <= trade.entry_ts <= bars[end - 1].ts])
        passed += int(
            fold["trades"] >= gate["fold_min_trades"]
            and fold["profit_factor"] >= gate["fold_min_profit_factor"]
            and fold["expectancy"] > gate["fold_min_expectancy"]
        )
    return passed


def main() -> None:
    run_id = uuid.uuid4()
    result_count = pass_count = unverified_count = 0
    with psycopg2.connect(DB) as conn:
        # Signal calculations dominate this stage. Do not retain an obsolete
        # transaction snapshot between SQL statements while the CPU is busy.
        conn.autocommit = True
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            markets=load_research_universe(cur,run_id=str(run_id),stage_code="DISCOVERY",
                min_bars=MIN_BARS,freshness_minutes=FRESHNESS_MINUTES)
            configurations = load_search_configuration(cur)

            for market in markets:
                cur.execute("SELECT ts,close,coalesce(volume,0) AS volume FROM public.market_bars WHERE symbol=%s AND timeframe=%s AND close IS NOT NULL AND source NOT IN ('unknown','synthetic_futures_backfill_v1') AND (%s IS NULL OR ts < %s::date + interval '1 day') ORDER BY ts", (market["symbol"], market["timeframe"],market["expiration_date"],market["expiration_date"]))
                bars = [Bar(row["ts"], float(row["close"]), float(row["volume"])) for row in cur.fetchall()]
                entry_policy = load_meta_entry_policy_v2(cur, market["symbol"], market["timeframe"], bars)
                cur.execute("""
                    SELECT DISTINCT ON (ts) ts,regime,confidence,source
                    FROM analytics_regime_snapshots_v2
                    WHERE symbol=%s AND timeframe=%s AND confidence >= %s
                    ORDER BY ts,confidence DESC,updated_at DESC
                """, (market["symbol"], market["timeframe"], MIN_CONFIDENCE))
                snapshots = cur.fetchall()
                regime_by_ts = {row["ts"]: row["regime"] for row in snapshots}
                source_by_ts = {row["ts"]: row["source"] for row in snapshots}
                confidence_by_ts = {row["ts"]: float(row["confidence"]) for row in snapshots}
                coverage = len(set(regime_by_ts).intersection(bar.ts for bar in bars)) / len(bars) if bars else 0.0

                train_end = int(len(bars) * 0.50)
                validation_end = int(len(bars) * 0.75)
                validation_start_ts = bars[train_end].ts
                oos_start_ts = bars[validation_end].ts
                cost_bps = 20.0 if str(market["symbol"]).endswith("USD") else 8.0
                roundtrip_cost = statistics.median(bar.close for bar in bars) * cost_bps / 10000.0

                for family, configuration in configurations:
                    targets = configuration["regime_policy"].get("target_symbols", [])
                    if targets and market["symbol"] not in targets:
                        continue
                    strategy_code, grid = configuration["strategy_code"], configuration["grid"]
                    reference_symbol = configuration["regime_policy"].get("reference_symbol")
                    strategy_bars = _attach_reference(cur,bars,reference_symbol,market["timeframe"])
                    allowed_regimes = configuration["regime_policy"].get("allowed_regimes")
                    if not allowed_regimes:
                        raise RuntimeError(f"REGIME_POLICY_ALLOWED_REGIMES_MISSING:{family}")
                    validation_gate = configuration["gate_policy"]["validation"]
                    oos_gate = configuration["gate_policy"]["oos"]
                    regime_gate = configuration["gate_policy"]["regime"]
                    for base_params in grid:
                        base_params = apply_meta_entry_policy_v2(dict(base_params), entry_policy)
                        params = {**base_params, "commission": roundtrip_cost, "slippage": 0.0,
                                  "contract_symbol": market["symbol"] if market["expiration_date"] else None,
                                  "contract_root": market["contract_root"],
                                  "contract_expiration": market["expiration_date"].isoformat() if market["expiration_date"] else None}
                        lookback = int(params["lookback"])
                        params["reference_symbol"] = reference_symbol
                        run = {"strategy_code": strategy_code, "parameter_json": params}
                        validation_all = [trade for trade in build_trades(run, strategy_bars[train_end - lookback:validation_end]) if trade.entry_ts >= validation_start_ts]
                        oos_all = [trade for trade in build_trades(run, strategy_bars[validation_end - lookback:]) if trade.entry_ts >= oos_start_ts]

                        for regime in allowed_regimes:
                            validation_trades = _filtered(validation_all, regime_by_ts, regime)
                            oos_trades = _filtered(oos_all, regime_by_ts, regime)
                            validation = metrics(validation_trades)
                            oos = metrics(oos_trades)
                            folds = _fold_passes(oos_trades, bars, validation_end, regime_gate)
                            observed_ts = [trade.entry_ts for trade in validation_trades + oos_trades]
                            trust_status = "VERIFIED" if coverage >= MIN_COVERAGE and observed_ts else "UNVERIFIED"
                            passed = (
                                trust_status == "VERIFIED"
                                and validation["trades"] >= validation_gate["min_trades"]
                                and validation["profit_factor"] >= validation_gate["min_profit_factor"]
                                and validation["expectancy"] > validation_gate["min_expectancy"]
                                and oos["trades"] >= oos_gate["min_trades"]
                                and oos["profit_factor"] >= oos_gate["min_profit_factor"]
                                and oos["expectancy"] > oos_gate["min_expectancy"]
                                and folds >= regime_gate["min_folds_passed"]
                            )
                            verdict = "OOS_PASS" if passed else ("UNVERIFIED" if trust_status == "UNVERIFIED" else "OOS_FAIL")
                            reason = "PASS" if passed else ("INSUFFICIENT_REGIME_COVERAGE" if trust_status == "UNVERIFIED" else "REGIME_OOS_GATE_FAILED")
                            hypothesis_score = score(oos["profit_factor"], oos["expectancy"], oos["trades"], folds, int(bool(oos_trades)))
                            sources = sorted({source_by_ts[ts] for ts in observed_ts if ts in source_by_ts})
                            min_conf = min((confidence_by_ts[ts] for ts in observed_ts if ts in confidence_by_ts), default=0.0)
                            cur.execute("""
                                INSERT INTO analytics.edge_regime_hypothesis_result_v2 (
                                    discovery_run_id,strategy_family,strategy_code,symbol,timeframe,parameter_json,
                                    regime_code,regime_source,min_regime_confidence,regime_coverage_ratio,
                                    validation_trades,validation_profit_factor,validation_expectancy,oos_trades,
                                    oos_profit_factor,oos_expectancy,oos_max_drawdown,folds_passed,folds_total,
                                    transaction_cost_bps,hypothesis_score,trust_status,verdict_code,reason_code,
                                    promotion_allowed,source_version
                                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,3,%s,%s,%s,%s,%s,false,%s)
                            """, (str(run_id),family,strategy_code,market["symbol"],market["timeframe"],psycopg2.extras.Json(base_params),
                                  regime,",".join(sources) or "NONE",min_conf,coverage,validation["trades"],validation["profit_factor"],
                                  validation["expectancy"],oos["trades"],oos["profit_factor"],oos["expectancy"],oos["max_drawdown"],
                                  folds,cost_bps,hypothesis_score,trust_status,verdict,reason,SOURCE_VERSION))
                            result_count += 1
                            pass_count += int(passed)
                            unverified_count += int(trust_status == "UNVERIFIED")

    print(f"discovery_run_id={run_id}")
    print(f"markets={len(markets)}")
    print(f"freshness_minutes={FRESHNESS_MINUTES}")
    print(f"strategy_regime_pairs={result_count}")
    print(f"oos_pass={pass_count}")
    print(f"unverified={unverified_count}")
    print("promotion_allowed=0")
    print("VERDICT=REGIME_AWARE_EDGE_DISCOVERY_V2_READY")


if __name__ == "__main__":
    main()
