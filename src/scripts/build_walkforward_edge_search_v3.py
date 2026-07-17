from __future__ import annotations

import statistics
import uuid
import os
import math
from collections import defaultdict

import psycopg2
import psycopg2.extras

from scripts.build_edge_hypothesis_discovery_v1 import load_search_configuration
from scripts.build_strategy_execution_runner_v1 import Bar, build_trades, load_execution_context, metrics


SOURCE_VERSION = "WALKFORWARD_EDGE_SEARCH_V4_TRUSTED_BARS"
NAMESPACE = uuid.UUID("e304fdfc-03db-5863-b65c-fe3ac08a0b93")
FOLDS = 5
FRESHNESS_MINUTES = int(os.getenv("EDGE_SEARCH_FRESHNESS_MINUTES", "15"))
TARGET_SYMBOL = os.getenv("EDGE_SEARCH_TARGET_SYMBOL", "").strip()


def _attach_reference(cursor, bars: list[Bar], symbol: str | None, timeframe: str) -> list[Bar]:
    if not symbol:
        return bars
    cursor.execute("""SELECT ts,close FROM public.market_bars WHERE symbol=%s AND timeframe=%s
        AND close IS NOT NULL AND source NOT IN ('unknown','synthetic_futures_backfill_v1') ORDER BY ts""",
        (symbol,timeframe))
    reference = {row["ts"]: float(row["close"]) for row in cursor.fetchall()}
    return [Bar(bar.ts,bar.close,bar.volume,reference.get(bar.ts)) for bar in bars]


def failure_reason(aggregate, folds_passed: int, final_holdout: bool, gate: dict) -> str:
    if aggregate["trades"] < gate["min_trades"]:
        return "INSUFFICIENT_TRADES"
    if aggregate["expectancy"] <= gate["min_expectancy"]:
        return "NEGATIVE_COST_ADJUSTED_EXPECTANCY"
    if aggregate["profit_factor"] < gate["min_profit_factor"]:
        return "PROFIT_FACTOR_BELOW_GATE"
    if folds_passed < gate["min_folds_passed"]:
        return "WALKFORWARD_FOLDS_UNSTABLE"
    if not final_holdout:
        return "FINAL_HOLDOUT_FAILED"
    return "WALKFORWARD_STABILITY_GATE_FAILED"


def methodology_evidence(trades, bars) -> dict:
    pnls = [float(trade.net_pnl) for trade in trades]
    mean = statistics.fmean(pnls) if pnls else 0.0
    stdev = statistics.pstdev(pnls) if len(pnls) > 1 else 0.0
    z_score = mean / (stdev / math.sqrt(len(pnls))) if stdev > 0 else 0.0
    p_value = 0.5 * math.erfc(z_score / math.sqrt(2.0)) if z_score > 0 else 1.0
    stress_multiplier = 1.5
    stressed = [float(t.gross_pnl) - stress_multiplier * (float(t.commission) + float(t.slippage)) for t in trades]
    wins = [value for value in stressed if value > 0]
    losses = [value for value in stressed if value <= 0]
    gross_loss = abs(sum(losses))
    stressed_pf = sum(wins) / gross_loss if gross_loss else (sum(wins) if wins else 0.0)
    volume_by_ts = {bar.ts: float(bar.volume) for bar in bars}
    capacities = [
        float(getattr(t,"capacity_rub",0.0))
        or volume_by_ts.get(t.entry_ts,0.0) * float(t.entry_price) * 0.01
        for t in trades
    ]
    fills = [float(getattr(t,"fill_ratio",1.0)) for t in trades]
    fallback_quotes = [str(getattr(t,"quote_source","LEGACY")) == "POLICY_FALLBACK" for t in trades]
    missing_specs = [str(getattr(t,"contract_spec_source","LEGACY")) == "MISSING_SPEC_FALLBACK" for t in trades]
    daily = defaultdict(float)
    for trade in trades:
        day = trade.exit_ts.date().isoformat() if hasattr(trade.exit_ts,"date") else str(trade.exit_ts)
        daily[day] += float(trade.net_pnl)
    return {
        "one_sided_p_value": round(p_value,10), "z_score": round(z_score,8),
        "pnl_stdev": round(stdev,8), "stress_cost_multiplier": stress_multiplier,
        "stressed_profit_factor": round(stressed_pf,8),
        "stressed_expectancy": round(statistics.fmean(stressed),8) if stressed else 0.0,
        "capacity_rub": round(statistics.median(capacities),2) if capacities else 0.0,
        "average_fill_ratio": round(statistics.fmean(fills),8) if fills else 0.0,
        "minimum_fill_ratio": round(min(fills),8) if fills else 0.0,
        "fallback_quote_share": round(sum(fallback_quotes)/len(fallback_quotes),8) if fallback_quotes else 1.0,
        "contract_spec_coverage": round(1-sum(missing_specs)/len(missing_specs),8) if missing_specs else 0.0,
        "average_spread_cost": round(statistics.fmean(float(getattr(t,"spread_cost",0.0)) for t in trades),8) if trades else 0.0,
        "average_impact_cost": round(statistics.fmean(float(getattr(t,"impact_cost",0.0)) for t in trades),8) if trades else 0.0,
        "signal_latency_bars": min((int(getattr(t,"latency_bars",0)) for t in trades),default=0),
        "daily_pnl": [{"date":day,"pnl":round(value,8)} for day,value in sorted(daily.items())],
    }


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
            configurations = load_search_configuration(cursor)
            for market in markets:
                execution_policy = load_execution_context(cursor, market["symbol"])
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
                for family, configuration in configurations:
                    targets = configuration["regime_policy"].get("target_symbols", [])
                    if targets and market["symbol"] not in targets:
                        continue
                    strategy_code, grid = configuration["strategy_code"], configuration["grid"]
                    reference_symbol = configuration["regime_policy"].get("reference_symbol")
                    strategy_bars = _attach_reference(cursor,bars,reference_symbol,market["timeframe"])
                    walkforward_gate = configuration["gate_policy"]["walkforward"]
                    for base_params in grid:
                        params = {
                            **base_params, "transaction_cost_bps": cost_bps,
                            "commission": roundtrip_cost, "slippage": 0.0,
                            "reference_symbol": reference_symbol,
                            "execution_policy": execution_policy,
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
                                    strategy_bars[max(0,start-lookback):end],
                                ) if start_ts<=trade.entry_ts<=end_ts
                            ]
                            value = metrics(trades)
                            fold_pass = (
                                value["trades"] >= walkforward_gate["fold_min_trades"]
                                and value["profit_factor"] >= walkforward_gate["fold_min_profit_factor"]
                                and value["expectancy"] > walkforward_gate["fold_min_expectancy"]
                            )
                            fold_rows.append({
                                "fold": fold_no+1,"start": start_ts.isoformat(),"end": end_ts.isoformat(),
                                "trades": value["trades"],"profit_factor": value["profit_factor"],
                                "expectancy": value["expectancy"],"max_drawdown": value["max_drawdown"],
                                "passed": fold_pass,
                            })
                            all_trades.extend(trades)
                        aggregate = metrics(all_trades)
                        evidence = methodology_evidence(all_trades,bars)
                        folds_passed = sum(int(row["passed"]) for row in fold_rows)
                        final_holdout = bool(fold_rows[-1]["passed"])
                        is_pass = (
                            aggregate["trades"] >= walkforward_gate["min_trades"]
                            and aggregate["profit_factor"] >= walkforward_gate["min_profit_factor"]
                            and aggregate["expectancy"] > walkforward_gate["min_expectancy"]
                            and folds_passed >= walkforward_gate["min_folds_passed"]
                            and (final_holdout or not walkforward_gate["final_holdout_required"])
                        )
                        reason = "WALKFORWARD_COST_ADJUSTED_PASS" if is_pass else failure_reason(aggregate,folds_passed,final_holdout,walkforward_gate)
                        identity = f"{search_run_id}:{strategy_code}:{market['symbol']}:{market['timeframe']}:{params}"
                        cursor.execute("""
                            INSERT INTO analytics.walkforward_edge_search_v3 (
                                result_id,search_run_id,strategy_family,strategy_code,symbol,timeframe,
                                parameter_json,transaction_cost_bps,total_trades,net_profit_factor,
                                net_expectancy,max_drawdown,folds_total,folds_passed,final_holdout_passed,
                                fold_metrics,verdict_code,promotion_allowed,reason_code,source_version
                                ,methodology_evidence
                            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false,%s,%s,%s)
                        """, (
                            str(uuid.uuid5(NAMESPACE,identity)),str(search_run_id),family,strategy_code,
                            market["symbol"],market["timeframe"],psycopg2.extras.Json(params),
                            cost_bps,aggregate["trades"],aggregate["profit_factor"],aggregate["expectancy"],
                            aggregate["max_drawdown"],FOLDS,folds_passed,final_holdout,
                            psycopg2.extras.Json(fold_rows),"OOS_PASS" if is_pass else "OOS_FAIL",reason,SOURCE_VERSION,
                            psycopg2.extras.Json(evidence),
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
