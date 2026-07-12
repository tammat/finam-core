from __future__ import annotations

import math
import os
import statistics
from statistics import NormalDist

import psycopg2
import psycopg2.extras

from marketcore.research_window_guard_v1 import require_off_market_research_window


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "RELATIVE_STRENGTH_PARAMETER_ADAPTER_V2"
TARGETS = ("SBER@MISX", "LKOH@MISX", "GAZP@MISX", "PLZL@MISX")
COST_BPS = 8.0


def pnl_metrics(rows: list[tuple[object, object, float]]) -> dict[str, float]:
    values = [value for _, _, value in rows]
    wins = [value for value in values if value > 0]
    losses = [value for value in values if value <= 0]
    gross_loss = abs(sum(losses))
    return {
        "trades": len(values),
        "profit_factor": sum(wins) / gross_loss if gross_loss else 0.0,
        "expectancy": statistics.fmean(values) if values else 0.0,
    }


def adjusted_p(rows: list[tuple[object, object, float]], trials: int) -> float:
    values = [value for _, _, value in rows]
    if len(values) < 2:
        return 1.0
    stdev = statistics.stdev(values)
    if stdev <= 0:
        return 1.0
    z = statistics.fmean(values) / (stdev / math.sqrt(len(values)))
    raw = 1.0 - NormalDist().cdf(z)
    return min(1.0, max(0.0, raw) * trials)


def build_rows(series: dict[str, dict], benchmark: str, params: dict) -> list[tuple[object, object, float]]:
    lookback = int(params["lookback"])
    hold = int(params["holding_bars"])
    threshold = float(params["rank_threshold"])
    timestamps = sorted(set(series[benchmark]).intersection(*(set(series[symbol]) for symbol in TARGETS)))
    rows: list[tuple[object, object, float]] = []
    no = lookback
    while no + hold < len(timestamps):
        ts = timestamps[no]
        past_ts = timestamps[no - lookback]
        exit_ts = timestamps[no + hold]
        benchmark_return = series[benchmark][ts] / series[benchmark][past_ts] - 1.0
        relative = []
        for symbol in TARGETS:
            value = (series[symbol][ts] / series[symbol][past_ts] - 1.0) - benchmark_return
            relative.append((value, symbol))
        relative.sort()
        denominator = max(1, len(relative) - 1)
        for rank, (_, symbol) in enumerate(relative):
            percentile = rank / denominator
            side = 1 if percentile >= threshold else (-1 if percentile <= 1.0 - threshold else 0)
            if not side:
                continue
            target_return_bps = (series[symbol][exit_ts] / series[symbol][ts] - 1.0) * 10000.0
            rows.append((ts, exit_ts, target_return_bps * side - COST_BPS))
        no += hold
    return rows


def main() -> None:
    require_off_market_research_window("RELATIVE_STRENGTH_PARAMETER_ADAPTER_V2")
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""SELECT execution_run_id,total_candidates FROM analytics.strategy_hypothesis_execution_run_v2
                ORDER BY created_at DESC LIMIT 1""")
            run = cur.fetchone()
            if not run:
                raise RuntimeError("NO_EXECUTION_RUN_V2")
            cur.execute("""SELECT candidate_hash,parameter_json FROM analytics.strategy_hypothesis_execution_result_v2
                WHERE execution_run_id=%s AND strategy_family='RELATIVE_STRENGTH' ORDER BY candidate_hash""",
                (run["execution_run_id"],))
            candidates = cur.fetchall()
            symbols = tuple(sorted(set(TARGETS + ("IMOEX", "IMOEX2"))))
            cur.execute("""SELECT symbol,ts,close FROM public.market_bars
                WHERE timeframe='M5' AND symbol=ANY(%s) AND close IS NOT NULL ORDER BY ts""", (list(symbols),))
            series: dict[str, dict] = {symbol: {} for symbol in symbols}
            for row in cur.fetchall():
                series[row["symbol"]][row["ts"]] = float(row["close"])

            passed = failed = 0
            for candidate in candidates:
                params = candidate["parameter_json"]
                benchmark = str(params["benchmark"])
                rows = build_rows(series, benchmark, params)
                entry_times = sorted({entry_ts for entry_ts, _, _ in rows})
                validation_start = entry_times[int(len(entry_times) * 0.50)]
                oos_start = entry_times[int(len(entry_times) * 0.75)]
                validation_rows = [row for row in rows if validation_start <= row[0] and row[1] < oos_start]
                oos_rows = [row for row in rows if row[0] >= oos_start]
                validation = pnl_metrics(validation_rows)
                oos = pnl_metrics(oos_rows)
                folds = 0
                if oos_rows:
                    for fold in range(3):
                        left = len(oos_rows) * fold // 3
                        right = len(oos_rows) * (fold + 1) // 3
                        metric = pnl_metrics(oos_rows[left:right])
                        folds += int(metric["trades"] >= 8 and metric["profit_factor"] >= 1.0 and metric["expectancy"] > 0)
                p_adj = adjusted_p(oos_rows, int(run["total_candidates"]))
                is_pass = (validation["trades"] >= 30 and validation["profit_factor"] >= 1.05
                           and oos["trades"] >= 30 and oos["profit_factor"] >= 1.10
                           and oos["expectancy"] > 0 and folds >= 2 and p_adj <= 0.05)
                verdict = "OOS_PASS" if is_pass else "OOS_FAIL"
                reason = "PASS" if is_pass else "RELATIVE_STRENGTH_STRICT_OOS_GATE_FAILED"
                passed += int(is_pass)
                failed += int(not is_pass)
                cur.execute("""UPDATE analytics.strategy_hypothesis_execution_result_v2 SET
                    symbol=%s,timeframe='M5',validation_trades=%s,validation_profit_factor=%s,
                    oos_trades=%s,oos_profit_factor=%s,oos_expectancy=%s,folds_passed=%s,
                    adjusted_p_value=%s,verdict_code=%s,reason_code=%s,source_version=%s
                    WHERE execution_run_id=%s AND candidate_hash=%s""",
                    ("MULTI_ASSET@MISX",validation["trades"],validation["profit_factor"],oos["trades"],
                     oos["profit_factor"],oos["expectancy"],folds,p_adj,verdict,reason,SOURCE_VERSION,
                     run["execution_run_id"],candidate["candidate_hash"]))
            cur.execute("""UPDATE analytics.strategy_hypothesis_execution_run_v2 SET
                oos_pass=(SELECT count(*) FROM analytics.strategy_hypothesis_execution_result_v2 WHERE execution_run_id=%s AND verdict_code='OOS_PASS'),
                oos_fail=(SELECT count(*) FROM analytics.strategy_hypothesis_execution_result_v2 WHERE execution_run_id=%s AND verdict_code='OOS_FAIL'),
                unverified=(SELECT count(*) FROM analytics.strategy_hypothesis_execution_result_v2 WHERE execution_run_id=%s AND verdict_code='UNVERIFIED')
                WHERE execution_run_id=%s""", (run["execution_run_id"],)*4)

    print(f"execution_run_id={run['execution_run_id']}")
    print(f"relative_strength_candidates={len(candidates)}")
    print(f"oos_pass={passed}")
    print(f"oos_fail={failed}")
    print("promotion_allowed=0")
    print("live_allowed=0")
    print("VERDICT=RELATIVE_STRENGTH_PARAMETER_ADAPTER_V2_OK")


if __name__ == "__main__":
    main()
