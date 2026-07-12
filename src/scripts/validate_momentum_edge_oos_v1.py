from __future__ import annotations

import os
from typing import Any

import psycopg2
import psycopg2.extras

from scripts.build_strategy_execution_runner_v1 import Bar, build_trades, metrics


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
BATCH_ID = os.getenv("RESEARCH_BATCH_ID", "20260712_MOMENTUM_THRESHOLD_RECALC_V2")
THRESHOLD = os.getenv("MOMENTUM_THRESHOLD", "0.5")
IN_SAMPLE_BARS = int(os.getenv("EDGE_OOS_IN_SAMPLE_BARS", "5000"))
FOLDS = int(os.getenv("EDGE_OOS_FOLDS", "3"))


def metric_line(name: str, value: Any) -> None:
    print(f"{name}={value}")


def main() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT strategy_code,symbol,timeframe,parameter_json
                FROM analytics.edge_observation_v1
                WHERE research_batch_id=%s
                  AND parameter_json->>'threshold'=%s
                """,
                (BATCH_ID, THRESHOLD),
            )
            observation = cur.fetchone()
            if not observation:
                raise RuntimeError("OOS_CANDIDATE_NOT_FOUND")

            cur.execute(
                """
                SELECT ts,close
                FROM public.market_bars
                WHERE symbol=%s AND timeframe=%s AND close IS NOT NULL
                ORDER BY ts ASC
                """,
                (observation["symbol"], observation["timeframe"]),
            )
            bars = [Bar(row["ts"], float(row["close"])) for row in cur.fetchall()]

    if len(bars) <= IN_SAMPLE_BARS:
        raise RuntimeError(
            f"OOS_BARS_NOT_AVAILABLE total={len(bars)} in_sample={IN_SAMPLE_BARS}"
        )

    params = observation["parameter_json"] or {}
    lookback = int(params.get("lookback", 20))
    oos_start = bars[IN_SAMPLE_BARS].ts
    evaluation_bars = bars[IN_SAMPLE_BARS - lookback :]
    run = {"strategy_code": observation["strategy_code"], "parameter_json": params}
    oos_trades = [trade for trade in build_trades(run, evaluation_bars) if trade.entry_ts >= oos_start]
    oos_metrics = metrics(oos_trades)

    fold_size = max(1, (len(bars) - IN_SAMPLE_BARS) // FOLDS)
    fold_passes = 0
    fold_results: list[dict[str, Any]] = []
    for fold_no in range(FOLDS):
        start = IN_SAMPLE_BARS + fold_no * fold_size
        end = len(bars) if fold_no == FOLDS - 1 else min(len(bars), start + fold_size)
        fold_start_ts = bars[start].ts
        fold_end_ts = bars[end - 1].ts
        context_start = max(0, start - lookback)
        fold_trades = [
            trade
            for trade in build_trades(run, bars[context_start:end])
            if fold_start_ts <= trade.entry_ts <= fold_end_ts
        ]
        fold_metrics = metrics(fold_trades)
        passed = (
            fold_metrics["trades"] >= 10
            and fold_metrics["profit_factor"] >= 1.0
            and fold_metrics["expectancy"] > 0
        )
        fold_passes += int(passed)
        fold_results.append({"fold": fold_no + 1, "passed": passed, **fold_metrics})

    oos_pass = (
        oos_metrics["trades"] >= 30
        and oos_metrics["profit_factor"] >= 1.10
        and oos_metrics["expectancy"] > 0
        and fold_passes >= 2
    )

    metric_line("candidate_threshold_pct", THRESHOLD)
    metric_line("bars_total", len(bars))
    metric_line("in_sample_bars", IN_SAMPLE_BARS)
    metric_line("oos_bars", len(bars) - IN_SAMPLE_BARS)
    metric_line("oos_start", oos_start.isoformat())
    metric_line("oos_end", bars[-1].ts.isoformat())
    metric_line("oos_trades", oos_metrics["trades"])
    metric_line("oos_profit_factor", round(oos_metrics["profit_factor"], 6))
    metric_line("oos_expectancy", round(oos_metrics["expectancy"], 6))
    metric_line("oos_max_drawdown", round(oos_metrics["max_drawdown"], 6))
    metric_line("folds_passed", f"{fold_passes}/{FOLDS}")
    for result in fold_results:
        metric_line(
            f"fold_{result['fold']}",
            "trades:{trades},pf:{pf:.6f},expectancy:{expectancy:.6f},passed:{passed}".format(
                trades=result["trades"],
                pf=result["profit_factor"],
                expectancy=result["expectancy"],
                passed=int(result["passed"]),
            ),
        )
    metric_line("runtime_changed", 0)
    metric_line("orders_changed", 0)
    metric_line("micro_live_allowed", 0)
    metric_line("VERDICT", "MOMENTUM_EDGE_OOS_PASS" if oos_pass else "MOMENTUM_EDGE_OOS_FAIL")


if __name__ == "__main__":
    main()
