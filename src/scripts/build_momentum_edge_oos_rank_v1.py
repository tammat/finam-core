from __future__ import annotations

import os

import psycopg2
import psycopg2.extras

from scripts.build_strategy_execution_runner_v1 import Bar, build_trades, metrics


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
BATCH_ID = os.getenv("RESEARCH_BATCH_ID")
IN_SAMPLE_BARS = int(os.getenv("EDGE_OOS_IN_SAMPLE_BARS", "5000"))
FOLDS = int(os.getenv("EDGE_OOS_FOLDS", "3"))
VALIDATION_VERSION = "MOMENTUM_CHRONOLOGICAL_OOS_V1"


def main() -> None:
    results = []
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT o.*
                FROM analytics.edge_observation_v1 o
                JOIN analytics.edge_candidate_v1 c ON c.observation_uuid=o.observation_uuid
                WHERE (%s IS NULL OR o.research_batch_id=%s)
                ORDER BY o.research_batch_id,(o.parameter_json->>'threshold')::numeric NULLS LAST,o.observation_uuid
                """,
                (BATCH_ID, BATCH_ID),
            )
            observations = cur.fetchall()
            if not observations:
                raise RuntimeError(f"OOS_CANDIDATES_EMPTY batch_id={BATCH_ID or 'ALL'}")

            bars_by_market = {}
            for observation in observations:
                market = (observation["symbol"], observation["timeframe"])
                if market not in bars_by_market:
                    cur.execute(
                        "SELECT ts,close FROM public.market_bars WHERE symbol=%s AND timeframe=%s AND close IS NOT NULL ORDER BY ts",
                        market,
                    )
                    bars_by_market[market] = [Bar(row["ts"], float(row["close"])) for row in cur.fetchall()]

                bars = bars_by_market[market]
                if len(bars) <= IN_SAMPLE_BARS:
                    raise RuntimeError(f"OOS_BARS_NOT_AVAILABLE market={market}")
                params = observation["parameter_json"] or {}
                specification_complete = (
                    "lookback" in params
                    and ("hold" in params or "holding_bars" in params)
                    and "threshold" in params
                )
                lookback = int(params.get("lookback", 20))
                run = {"strategy_code": observation["strategy_code"], "parameter_json": params}
                oos_start = bars[IN_SAMPLE_BARS].ts
                oos_trades = [
                    trade
                    for trade in build_trades(run, bars[IN_SAMPLE_BARS - lookback :])
                    if trade.entry_ts >= oos_start
                ]
                oos = metrics(oos_trades)

                fold_size = max(1, (len(bars) - IN_SAMPLE_BARS) // FOLDS)
                folds_passed = 0
                for fold_no in range(FOLDS):
                    start = IN_SAMPLE_BARS + fold_no * fold_size
                    end = len(bars) if fold_no == FOLDS - 1 else min(len(bars), start + fold_size)
                    fold_start = bars[start].ts
                    fold_end = bars[end - 1].ts
                    fold_trades = [
                        trade
                        for trade in build_trades(run, bars[max(0, start - lookback) : end])
                        if fold_start <= trade.entry_ts <= fold_end
                    ]
                    fold = metrics(fold_trades)
                    folds_passed += int(
                        fold["trades"] >= 10
                        and fold["profit_factor"] >= 1.0
                        and fold["expectancy"] > 0
                    )

                passed = specification_complete and (
                    oos["trades"] >= 30
                    and oos["profit_factor"] >= 1.10
                    and oos["expectancy"] > 0
                    and folds_passed >= 2
                )
                verdict = "OOS_PASS" if passed else "OOS_FAIL"
                reason = (
                    "OOS_SPECIFICATION_INCOMPLETE: lookback, hold/holding_bars and threshold are required"
                    if not specification_complete
                    else (
                        "OOS metrics and temporal folds passed"
                        if passed
                        else "OOS PF/expectancy or temporal fold stability failed"
                    )
                )
                cur.execute(
                    """
                    INSERT INTO analytics.edge_oos_result_v1 (
                        observation_uuid,research_batch_id,strategy_code,symbol,timeframe,
                        parameter_hash,parameter_json,validation_version,in_sample_bars,oos_bars,
                        oos_start,oos_end,oos_trades,oos_profit_factor,oos_expectancy,
                        oos_max_drawdown,folds_total,folds_passed,verdict_code,promotion_allowed,
                        reason,updated_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
                    ON CONFLICT (observation_uuid,validation_version) DO UPDATE SET
                        oos_bars=EXCLUDED.oos_bars,oos_start=EXCLUDED.oos_start,oos_end=EXCLUDED.oos_end,
                        oos_trades=EXCLUDED.oos_trades,oos_profit_factor=EXCLUDED.oos_profit_factor,
                        oos_expectancy=EXCLUDED.oos_expectancy,oos_max_drawdown=EXCLUDED.oos_max_drawdown,
                        folds_passed=EXCLUDED.folds_passed,verdict_code=EXCLUDED.verdict_code,
                        promotion_allowed=EXCLUDED.promotion_allowed,reason=EXCLUDED.reason,updated_at=now()
                    """,
                    (
                        observation["observation_uuid"], observation["research_batch_id"], observation["strategy_code"],
                        observation["symbol"], observation["timeframe"], observation["parameter_hash"],
                        psycopg2.extras.Json(params), VALIDATION_VERSION, IN_SAMPLE_BARS,
                        len(bars) - IN_SAMPLE_BARS, oos_start, bars[-1].ts, oos["trades"],
                        oos["profit_factor"], oos["expectancy"], oos["max_drawdown"], FOLDS,
                        folds_passed, verdict, passed, reason,
                    ),
                )
                cur.execute(
                    """
                    UPDATE analytics.edge_candidate_v1
                    SET candidate_status=%s,
                        validation_stage='OOS_COMPLETE',
                        paper_allowed=%s,
                        validation_reason=%s,
                        validation_formula_version=%s,
                        updated_at=now()
                    WHERE observation_uuid=%s
                    """,
                    (verdict, passed, reason, VALIDATION_VERSION, observation["observation_uuid"]),
                )
                results.append((params.get("threshold"), oos, folds_passed, verdict))

    results.sort(key=lambda item: (item[3] != "OOS_PASS", -item[1]["profit_factor"]))
    for rank, (threshold, oos, folds_passed, verdict) in enumerate(results, start=1):
        print(
            f"rank={rank}|threshold={threshold}|trades={oos['trades']}|pf={oos['profit_factor']:.6f}|"
            f"expectancy={oos['expectancy']:.6f}|folds={folds_passed}/{FOLDS}|verdict={verdict}"
        )
    print(f"rows={len(results)}")
    print(f"passed={sum(1 for result in results if result[3] == 'OOS_PASS')}")
    print(f"failed={sum(1 for result in results if result[3] == 'OOS_FAIL')}")
    print("runtime_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MOMENTUM_EDGE_OOS_RANK_V1_READY")


if __name__ == "__main__":
    main()
