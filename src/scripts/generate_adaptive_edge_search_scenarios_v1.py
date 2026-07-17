from __future__ import annotations

import json
import os
import uuid
from datetime import datetime

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
VERSION = "ADAPTIVE_EDGE_SEARCH_V1_DEVELOPMENT_FOLDS_ONLY"
NAMESPACE = uuid.UUID("0d116af2-76dd-48bb-b9d1-33a987676659")
MIN_FUTURE_BARS = int(os.getenv("ADAPTIVE_EDGE_MIN_FUTURE_BARS", "500"))
MAX_NEW_SCENARIOS = int(os.getenv("ADAPTIVE_EDGE_MAX_NEW_SCENARIOS", "3"))


def development_metrics(folds: list[dict]) -> dict | None:
    """Fold 5 is a consumed holdout and is deliberately excluded from selection."""
    development = [item for item in folds if int(item["fold"]) in (1, 2, 3, 4)]
    if len(development) != 4:
        return None
    trades = sum(int(item["trades"]) for item in development)
    if not trades:
        return None
    weighted_pf = sum(float(item["profit_factor"]) * int(item["trades"]) for item in development) / trades
    weighted_expectancy = sum(float(item["expectancy"]) * int(item["trades"]) for item in development) / trades
    return {
        "selection_folds": [1, 2, 3, 4],
        "trades": trades,
        "weighted_profit_factor": round(weighted_pf, 8),
        "weighted_expectancy": round(weighted_expectancy, 8),
        "folds_passed": sum(bool(item["passed"]) for item in development),
    }


def bounded_grid(parameters: dict) -> list[dict]:
    clean = {key: value for key, value in parameters.items() if key not in {
        "commission", "slippage", "transaction_cost_bps", "adaptive_scenario_id"
    }}
    lookback = int(clean["lookback"])
    hold = int(clean["hold"])
    threshold = float(clean["threshold"])
    lookbacks = sorted({max(20, int(round(lookback * ratio / 10) * 10)) for ratio in (.75, 1, 1.25, 1.5)})
    holds = sorted({max(3, int(round(hold * ratio))) for ratio in (2 / 3, 1, 4 / 3)})
    thresholds = sorted({round(max(.1, threshold * ratio), 4) for ratio in (.8, 1, 1.2, 1.5)})
    return [{**clean, "lookback": lb, "hold": hd, "threshold": th}
            for lb in lookbacks for hd in holds for th in thresholds]


def activate_ready(cursor) -> int:
    cursor.execute("""
        UPDATE analytics.edge_search_adaptive_scenario_v1 s
        SET status_code='ACTIVE',reason_code='FUTURE_CONFIRMATION_WINDOW_READY',
            activated_at=clock_timestamp(),updated_at=clock_timestamp()
        WHERE s.status_code='WAITING_FUTURE_DATA'
          AND (SELECT count(*) FROM public.market_bars b
               WHERE b.symbol=s.target_symbol AND b.timeframe='M5'
                 AND b.ts>s.confirmation_after_ts
                 AND b.source NOT IN ('unknown','synthetic_futures_backfill_v1')) >= s.minimum_future_bars
        RETURNING adaptive_scenario_id
    """)
    return len(cursor.fetchall())


def close_evaluated(cursor, search_run_id: str) -> int:
    cursor.execute("""
        WITH outcomes AS (
          SELECT s.adaptive_scenario_id,
                 bool_or(w.verdict_code='OOS_PASS') AS passed
          FROM analytics.edge_search_adaptive_scenario_v1 s
          JOIN analytics.walkforward_edge_search_v3 w
            ON w.search_run_id=%s
           AND w.parameter_json->>'adaptive_scenario_id'=s.adaptive_scenario_id::text
          WHERE s.status_code='ACTIVE'
          GROUP BY s.adaptive_scenario_id
        )
        UPDATE analytics.edge_search_adaptive_scenario_v1 s
        SET status_code=CASE WHEN o.passed THEN 'EVALUATED_PASS' ELSE 'EVALUATED_FAIL' END,
            reason_code=CASE WHEN o.passed THEN 'FUTURE_DATA_PASS' ELSE 'FUTURE_DATA_NO_PASS' END,
            evaluated_at=clock_timestamp(),updated_at=clock_timestamp()
        FROM outcomes o WHERE s.adaptive_scenario_id=o.adaptive_scenario_id
        RETURNING s.adaptive_scenario_id
    """, (search_run_id,))
    return len(cursor.fetchall())


def main() -> None:
    parent_run_id = os.environ["EDGE_SEARCH_SCENARIO_RUN_ID"]
    search_run_id = os.environ["EDGE_SEARCH_WALKFORWARD_RUN_ID"]
    created = 0
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            evaluated = close_evaluated(cursor, search_run_id)
            activated = activate_ready(cursor)
            cursor.execute("""
                SELECT w.*,r.gate_policy
                FROM analytics.walkforward_edge_search_v3 w
                JOIN analytics.edge_search_algorithm_registry_v1 r
                  ON r.algorithm_code=w.strategy_family
                WHERE w.search_run_id=%s AND w.verdict_code='OOS_FAIL'
                  AND NOT EXISTS (
                    SELECT 1 FROM analytics.edge_search_adaptive_scenario_v1 s
                    WHERE s.parent_result_id=w.result_id AND s.config_version=%s)
                ORDER BY w.created_at,w.result_id
            """, (search_run_id, VERSION))
            eligible = []
            for row in cursor.fetchall():
                metrics = development_metrics(row["fold_metrics"])
                if not metrics:
                    continue
                if (metrics["trades"] >= 200 and metrics["folds_passed"] >= 2
                        and metrics["weighted_profit_factor"] >= 1.02
                        and metrics["weighted_expectancy"] > 0):
                    eligible.append((metrics["weighted_expectancy"], row, metrics))
            eligible.sort(key=lambda item: item[0], reverse=True)
            for _, row, metrics in eligible[:MAX_NEW_SCENARIOS]:
                fold5 = next(item for item in row["fold_metrics"] if int(item["fold"]) == 5)
                scenario_id = uuid.uuid5(NAMESPACE, f"{row['result_id']}:{VERSION}")
                policy = {
                    "generator": VERSION,
                    "gate_policy": row["gate_policy"],
                    "max_new_scenarios_per_cycle": MAX_NEW_SCENARIOS,
                    "selection_uses_final_holdout": False,
                }
                holdout = {
                    "selection_folds": [1, 2, 3, 4],
                    "consumed_holdout_fold": 5,
                    "confirmation_mode": "FUTURE_DATA_ONLY",
                    "confirmation_after": fold5["end"],
                }
                cursor.execute("""
                    INSERT INTO analytics.edge_search_adaptive_scenario_v1 (
                      adaptive_scenario_id,parent_run_id,parent_search_run_id,parent_result_id,
                      algorithm_code,strategy_code,target_symbol,parameter_grid,selection_metrics,
                      generation_policy,holdout_policy,confirmation_after_ts,minimum_future_bars,
                      status_code,reason_code,config_version)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                            'WAITING_FUTURE_DATA','OLD_HOLDOUT_CONSUMED_WAITING_FUTURE_DATA',%s)
                    ON CONFLICT (parent_result_id,config_version) DO NOTHING
                """, (str(scenario_id),parent_run_id,search_run_id,str(row["result_id"]),
                      row["strategy_family"],row["strategy_code"],row["symbol"],
                      psycopg2.extras.Json(bounded_grid(row["parameter_json"])),
                      psycopg2.extras.Json(metrics),psycopg2.extras.Json(policy),
                      psycopg2.extras.Json(holdout),datetime.fromisoformat(fold5["end"]),
                      MIN_FUTURE_BARS,VERSION))
                created += cursor.rowcount
    print(f"adaptive_scenarios_created={created}")
    print(f"adaptive_scenarios_activated={activated}")
    print(f"adaptive_scenarios_evaluated={evaluated}")
    print("selection_folds=1,2,3,4")
    print("confirmation_mode=FUTURE_DATA_ONLY")
    print("VERDICT=ADAPTIVE_EDGE_SCENARIO_GENERATOR_V1_READY")


if __name__ == "__main__":
    main()
