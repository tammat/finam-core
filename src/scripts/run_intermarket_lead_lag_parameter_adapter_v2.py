from __future__ import annotations

import math
import os
import statistics
from datetime import timedelta
from statistics import NormalDist

import psycopg2
import psycopg2.extras

from marketcore.research_window_guard_v1 import require_off_market_research_window


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "INTERMARKET_LEAD_LAG_PARAMETER_ADAPTER_V2"
COST_BPS = 8.0
RELATIONSHIPS = (
    ("IMOEX2", "SBER@MISX", 1), ("IMOEX2", "LKOH@MISX", 1),
    ("IMOEX2", "GAZP@MISX", 1), ("IMOEX2", "PLZL@MISX", 1),
    ("RTSI", "SBER@MISX", 1), ("RTSI", "LKOH@MISX", 1),
    ("RTSI", "GAZP@MISX", 1), ("RTSI", "PLZL@MISX", 1),
    ("USDRUBF@RTSX", "LKOH@MISX", 1), ("USDRUBF@RTSX", "GAZP@MISX", 1),
    ("USDRUBF@RTSX", "PLZL@MISX", 1),
    ("BR_ROLLING@RTSX", "LKOH@MISX", 1),
    ("NG_ROLLING@RTSX", "GAZP@MISX", 1),
)


def metrics(rows: list[tuple[object, object, float]]) -> dict[str, float]:
    values = [value for _, _, value in rows]
    wins = [value for value in values if value > 0]
    losses = [value for value in values if value <= 0]
    loss = abs(sum(losses))
    return {"trades": len(values), "profit_factor": sum(wins) / loss if loss else 0.0,
            "expectancy": statistics.fmean(values) if values else 0.0}


def adjusted_p(rows: list[tuple[object, object, float]], trials: int) -> float:
    values = [value for _, _, value in rows]
    if len(values) < 2:
        return 1.0
    stdev = statistics.stdev(values)
    if stdev <= 0:
        return 1.0
    z = statistics.fmean(values) / (stdev / math.sqrt(len(values)))
    return min(1.0, max(0.0, 1.0 - NormalDist().cdf(z)) * trials)


def relationship_rows(series: dict[str, dict], source: str, target: str, direction: int, params: dict):
    impulse = int(params["impulse_bars"])
    lag = int(params["lag_bars"])
    hold = int(params["holding_bars"])
    threshold = float(params["threshold"])
    timestamps = sorted(set(series[source]).intersection(series[target]))
    rows = []
    for no in range(impulse, len(timestamps) - lag - hold):
        signal_ts = timestamps[no]
        source_return = series[source][signal_ts] / series[source][timestamps[no - impulse]] - 1.0
        if abs(source_return) < threshold:
            continue
        entry_ts = timestamps[no + lag]
        exit_ts = timestamps[no + lag + hold]
        side = (1 if source_return > 0 else -1) * direction
        pnl_bps = (series[target][exit_ts] / series[target][entry_ts] - 1.0) * 10000.0 * side - COST_BPS
        rows.append((entry_ts, exit_ts, pnl_bps))
    return rows, timestamps


def main() -> None:
    require_off_market_research_window("INTERMARKET_LEAD_LAG_PARAMETER_ADAPTER_V2")
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""SELECT execution_run_id,total_candidates FROM analytics.strategy_hypothesis_execution_run_v2
                ORDER BY created_at DESC LIMIT 1""")
            run = cur.fetchone()
            if not run:
                raise RuntimeError("NO_EXECUTION_RUN_V2")
            cur.execute("""SELECT candidate_hash,parameter_json FROM analytics.strategy_hypothesis_execution_result_v2
                WHERE execution_run_id=%s AND strategy_family='INTERMARKET_LEAD_LAG' ORDER BY candidate_hash""",
                (run["execution_run_id"],))
            candidates = cur.fetchall()
            symbols = sorted({value for source, target, _ in RELATIONSHIPS for value in (source, target)})
            cur.execute("""SELECT symbol,ts,close FROM public.market_bars WHERE timeframe='M5'
                AND symbol=ANY(%s) AND close IS NOT NULL ORDER BY ts""", (symbols,))
            series: dict[str, dict] = {symbol: {} for symbol in symbols}
            for row in cur.fetchall():
                series[row["symbol"]][row["ts"]] = float(row["close"])

            passed = failed = 0
            for candidate in candidates:
                params = candidate["parameter_json"]
                validation_rows = []
                oos_rows = []
                for source, target, direction in RELATIONSHIPS:
                    rows, timestamps = relationship_rows(series, source, target, direction, params)
                    if len(timestamps) < 100:
                        continue
                    validation_start = timestamps[int(len(timestamps) * 0.50)]
                    oos_start = timestamps[int(len(timestamps) * 0.75)]
                    embargo = timedelta(minutes=5 * int(params["holding_bars"]))
                    validation_rows.extend(row for row in rows if validation_start + embargo <= row[0] and row[1] < oos_start)
                    oos_rows.extend(row for row in rows if row[0] >= oos_start + embargo)
                validation_rows.sort(key=lambda row: row[0])
                oos_rows.sort(key=lambda row: row[0])
                validation = metrics(validation_rows)
                oos = metrics(oos_rows)
                folds = 0
                if oos_rows:
                    entry_times = sorted({row[0] for row in oos_rows})
                    for fold in range(3):
                        left_ts = entry_times[len(entry_times) * fold // 3]
                        right_index = len(entry_times) * (fold + 1) // 3
                        right_ts = entry_times[right_index] if right_index < len(entry_times) else None
                        subset = [row for row in oos_rows if row[0] >= left_ts and (right_ts is None or row[0] < right_ts)]
                        result = metrics(subset)
                        folds += int(result["trades"] >= 8 and result["profit_factor"] >= 1.0 and result["expectancy"] > 0)
                p_adj = adjusted_p(oos_rows, int(run["total_candidates"]))
                is_pass = (validation["trades"] >= 30 and validation["profit_factor"] >= 1.05
                           and oos["trades"] >= 30 and oos["profit_factor"] >= 1.10
                           and oos["expectancy"] > 0 and folds >= 2 and p_adj <= 0.05)
                verdict = "OOS_PASS" if is_pass else "OOS_FAIL"
                reason = "PASS" if is_pass else "LEAD_LAG_STRICT_OOS_GATE_FAILED"
                passed += int(is_pass)
                failed += int(not is_pass)
                cur.execute("""UPDATE analytics.strategy_hypothesis_execution_result_v2 SET
                    symbol='INTERMARKET_BASKET',timeframe='M5',validation_trades=%s,validation_profit_factor=%s,
                    oos_trades=%s,oos_profit_factor=%s,oos_expectancy=%s,folds_passed=%s,
                    adjusted_p_value=%s,verdict_code=%s,reason_code=%s,source_version=%s
                    WHERE execution_run_id=%s AND candidate_hash=%s""",
                    (validation["trades"],validation["profit_factor"],oos["trades"],oos["profit_factor"],
                     oos["expectancy"],folds,p_adj,verdict,reason,SOURCE_VERSION,run["execution_run_id"],candidate["candidate_hash"]))
            cur.execute("""UPDATE analytics.strategy_hypothesis_execution_run_v2 SET
                oos_pass=(SELECT count(*) FROM analytics.strategy_hypothesis_execution_result_v2 WHERE execution_run_id=%s AND verdict_code='OOS_PASS'),
                oos_fail=(SELECT count(*) FROM analytics.strategy_hypothesis_execution_result_v2 WHERE execution_run_id=%s AND verdict_code='OOS_FAIL'),
                unverified=(SELECT count(*) FROM analytics.strategy_hypothesis_execution_result_v2 WHERE execution_run_id=%s AND verdict_code='UNVERIFIED')
                WHERE execution_run_id=%s""", (run["execution_run_id"],)*4)

    print(f"execution_run_id={run['execution_run_id']}")
    print(f"relationships={len(RELATIONSHIPS)}")
    print(f"lead_lag_candidates={len(candidates)}")
    print(f"oos_pass={passed}")
    print(f"oos_fail={failed}")
    print("promotion_allowed=0")
    print("live_allowed=0")
    print("VERDICT=INTERMARKET_LEAD_LAG_PARAMETER_ADAPTER_V2_OK")


if __name__ == "__main__":
    main()
