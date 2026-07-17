from __future__ import annotations

import statistics
import uuid
import os

import psycopg2
import psycopg2.extras

from scripts.build_edge_hypothesis_discovery_v1 import GRIDS
from scripts.build_strategy_execution_runner_v1 import Bar, build_trades, metrics


SOURCE_VERSION = "WALKFORWARD_EDGE_SEARCH_V4_TRUSTED_BARS"
NAMESPACE = uuid.UUID("e304fdfc-03db-5863-b65c-fe3ac08a0b93")
FOLDS = 5
FRESHNESS_MINUTES = int(os.getenv("EDGE_SEARCH_FRESHNESS_MINUTES", "15"))
TARGET_SYMBOL = os.getenv("EDGE_SEARCH_TARGET_SYMBOL", "").strip()


def main() -> None:
    search_run_id = uuid.uuid4()
    passed = total = 0
    with psycopg2.connect("postgresql:///finam_core") as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT symbol,timeframe,count(*) bars
                FROM public.market_bars WHERE timeframe='M5'
                  AND source NOT IN ('unknown','synthetic_futures_backfill_v1')
                  AND (%s='' OR symbol=%s)
                GROUP BY symbol,timeframe
                HAVING count(*)>=6000
                   AND max(ts)>=clock_timestamp()-(%s * interval '1 minute')
                ORDER BY count(*) DESC LIMIT 12
            """, (TARGET_SYMBOL,TARGET_SYMBOL,FRESHNESS_MINUTES))
            markets = cursor.fetchall()
            for market in markets:
                cursor.execute("""
                    SELECT ts,close,coalesce(volume,0) AS volume FROM public.market_bars
                    WHERE symbol=%s AND timeframe=%s AND close IS NOT NULL
                      AND source NOT IN ('unknown','synthetic_futures_backfill_v1')
                    ORDER BY ts
                """, (market["symbol"], market["timeframe"]))
                bars = [Bar(row["ts"], float(row["close"]), float(row["volume"])) for row in cursor.fetchall()]
                evaluation_start = int(len(bars) * 0.40)
                fold_span = max(1, (len(bars)-evaluation_start)//FOLDS)
                cost_bps = 20.0 if str(market["symbol"]).endswith("USD") else 8.0
                roundtrip_cost = statistics.median(bar.close for bar in bars) * cost_bps / 10000.0
                for family, (strategy_code, grid) in GRIDS.items():
                    for base_params in grid:
                        params = {
                            **base_params, "transaction_cost_bps": cost_bps,
                            "commission": roundtrip_cost, "slippage": 0.0,
                        }
                        lookback = int(params["lookback"])
                        fold_rows = []
                        all_trades = []
                        for fold_no in range(FOLDS):
                            start = evaluation_start + fold_no*fold_span
                            end = len(bars) if fold_no == FOLDS-1 else min(len(bars),start+fold_span)
                            start_ts,end_ts = bars[start].ts,bars[end-1].ts
                            trades = [
                                trade for trade in build_trades(
                                    {"strategy_code": strategy_code,"parameter_json": params},
                                    bars[max(0,start-lookback):end],
                                ) if start_ts<=trade.entry_ts<=end_ts
                            ]
                            value = metrics(trades)
                            fold_pass = value["trades"]>=12 and value["profit_factor"]>=1.0 and value["expectancy"]>0
                            fold_rows.append({
                                "fold": fold_no+1,"start": start_ts.isoformat(),"end": end_ts.isoformat(),
                                "trades": value["trades"],"profit_factor": value["profit_factor"],
                                "expectancy": value["expectancy"],"max_drawdown": value["max_drawdown"],
                                "passed": fold_pass,
                            })
                            all_trades.extend(trades)
                        aggregate = metrics(all_trades)
                        folds_passed = sum(int(row["passed"]) for row in fold_rows)
                        final_holdout = bool(fold_rows[-1]["passed"])
                        is_pass = (
                            aggregate["trades"]>=80 and aggregate["profit_factor"]>=1.15
                            and aggregate["expectancy"]>0 and folds_passed>=4 and final_holdout
                        )
                        reason = "WALKFORWARD_COST_ADJUSTED_PASS" if is_pass else "WALKFORWARD_STABILITY_GATE_FAILED"
                        identity = f"{search_run_id}:{strategy_code}:{market['symbol']}:{market['timeframe']}:{params}"
                        cursor.execute("""
                            INSERT INTO analytics.walkforward_edge_search_v3 (
                                result_id,search_run_id,strategy_family,strategy_code,symbol,timeframe,
                                parameter_json,transaction_cost_bps,total_trades,net_profit_factor,
                                net_expectancy,max_drawdown,folds_total,folds_passed,final_holdout_passed,
                                fold_metrics,verdict_code,promotion_allowed,reason_code,source_version
                            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false,%s,%s)
                        """, (
                            str(uuid.uuid5(NAMESPACE,identity)),str(search_run_id),family,strategy_code,
                            market["symbol"],market["timeframe"],psycopg2.extras.Json(params),
                            cost_bps,aggregate["trades"],aggregate["profit_factor"],aggregate["expectancy"],
                            aggregate["max_drawdown"],FOLDS,folds_passed,final_holdout,
                            psycopg2.extras.Json(fold_rows),"OOS_PASS" if is_pass else "OOS_FAIL",reason,SOURCE_VERSION,
                        ))
                        total += 1
                        passed += int(is_pass)
    print(f"search_run_id={search_run_id}")
    print(f"freshness_minutes={FRESHNESS_MINUTES}")
    print(f"target_symbol={TARGET_SYMBOL or 'ALL'}")
    print(f"candidates_evaluated={total}")
    print(f"oos_pass={passed}")
    print("promotion_allowed=0")
    print("paper_allowed=0")
    print("runtime_allowed=0")
    print("live_allowed=0")
    print("VERDICT=WALKFORWARD_EDGE_SEARCH_V3_READY")


if __name__ == "__main__":
    main()
