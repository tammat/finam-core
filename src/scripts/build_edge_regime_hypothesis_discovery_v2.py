from __future__ import annotations

import os
import statistics
import uuid
from collections import defaultdict

import psycopg2
import psycopg2.extras

from scripts.build_edge_hypothesis_discovery_v1 import GRIDS, score
from scripts.build_strategy_execution_runner_v1 import Bar, Trade, build_trades, metrics


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "REGIME_AWARE_EDGE_DISCOVERY_V2"
MIN_BARS = int(os.getenv("EDGE_HYPOTHESIS_MIN_BARS", "6000"))
MAX_MARKETS = int(os.getenv("EDGE_HYPOTHESIS_MAX_MARKETS", "12"))
FRESHNESS_MINUTES = int(os.getenv("EDGE_SEARCH_FRESHNESS_MINUTES", "15"))
MIN_CONFIDENCE = float(os.getenv("EDGE_REGIME_MIN_CONFIDENCE", "0.60"))
MIN_COVERAGE = float(os.getenv("EDGE_REGIME_MIN_COVERAGE", "0.80"))

ALLOWED_REGIMES = {
    "MOMENTUM": ("trend_up", "trend_down", "trend_up_expansion", "trend_down_expansion"),
    "MEAN_REVERSION": ("range_normal", "range_compression", "compression"),
    "BREAKOUT": ("compression", "trend_up_expansion", "trend_down_expansion"),
}


def _filtered(trades: list[Trade], regime_by_ts: dict[object, str], regime: str) -> list[Trade]:
    return [trade for trade in trades if regime_by_ts.get(trade.entry_ts) == regime]


def _fold_passes(trades: list[Trade], bars: list[Bar], start_index: int) -> int:
    if not trades:
        return 0
    fold_span = max(1, (len(bars) - start_index) // 3)
    passed = 0
    for fold_no in range(3):
        start = start_index + fold_no * fold_span
        end = len(bars) if fold_no == 2 else min(len(bars), start + fold_span)
        fold = metrics([trade for trade in trades if bars[start].ts <= trade.entry_ts <= bars[end - 1].ts])
        passed += int(fold["trades"] >= 8 and fold["profit_factor"] >= 1.0 and fold["expectancy"] > 0)
    return passed


def main() -> None:
    run_id = uuid.uuid4()
    result_count = pass_count = unverified_count = 0
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT symbol,timeframe,count(*) AS bars
                FROM public.market_bars WHERE timeframe='M5'
                GROUP BY symbol,timeframe
                HAVING count(*) >= %s
                   AND max(ts) >= clock_timestamp()-(%s * interval '1 minute')
                ORDER BY count(*) DESC LIMIT %s
            """, (MIN_BARS, FRESHNESS_MINUTES, MAX_MARKETS))
            markets = cur.fetchall()

            for market in markets:
                cur.execute("SELECT ts,close FROM public.market_bars WHERE symbol=%s AND timeframe=%s AND close IS NOT NULL ORDER BY ts", (market["symbol"], market["timeframe"]))
                bars = [Bar(row["ts"], float(row["close"])) for row in cur.fetchall()]
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

                for family, (strategy_code, grid) in GRIDS.items():
                    for base_params in grid:
                        params = {**base_params, "commission": roundtrip_cost, "slippage": 0.0}
                        lookback = int(params["lookback"])
                        run = {"strategy_code": strategy_code, "parameter_json": params}
                        validation_all = [trade for trade in build_trades(run, bars[train_end - lookback:validation_end]) if trade.entry_ts >= validation_start_ts]
                        oos_all = [trade for trade in build_trades(run, bars[validation_end - lookback:]) if trade.entry_ts >= oos_start_ts]

                        for regime in ALLOWED_REGIMES[family]:
                            validation_trades = _filtered(validation_all, regime_by_ts, regime)
                            oos_trades = _filtered(oos_all, regime_by_ts, regime)
                            validation = metrics(validation_trades)
                            oos = metrics(oos_trades)
                            folds = _fold_passes(oos_trades, bars, validation_end)
                            observed_ts = [trade.entry_ts for trade in validation_trades + oos_trades]
                            trust_status = "VERIFIED" if coverage >= MIN_COVERAGE and observed_ts else "UNVERIFIED"
                            passed = (
                                trust_status == "VERIFIED"
                                and validation["trades"] >= 30 and validation["profit_factor"] >= 1.05 and validation["expectancy"] > 0
                                and oos["trades"] >= 30 and oos["profit_factor"] >= 1.10 and oos["expectancy"] > 0
                                and folds >= 2
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
