from __future__ import annotations

import hashlib
import itertools
import json
import os
import uuid
from collections import Counter
from datetime import datetime

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
VERSION = "NEXT_EDGE_RESEARCH_PLAN_V1_FAIL_DRIVEN"
NAMESPACE = uuid.UUID("33eab308-54f5-47ad-a9ae-f7f42ac19fa7")
MIN_FUTURE_BARS = int(os.getenv("ADAPTIVE_EDGE_MIN_FUTURE_BARS", "500"))
MAX_NEW_SCENARIOS = int(os.getenv("ADAPTIVE_EDGE_MAX_NEW_SCENARIOS", "3"))
MAX_VARIANTS_PER_ITEM = int(os.getenv("EDGE_NEXT_PLAN_MAX_VARIANTS", "48"))


REASON_POLICY = {
    "INSUFFICIENT_TRADES": ("EXPAND_SIGNAL_FREQUENCY", 4, "Увеличить частоту сигналов в допустимых границах."),
    "NEGATIVE_COST_ADJUSTED_EXPECTANCY": ("STRENGTHEN_ENTRY_SHORTEN_HOLD", 3, "Усилить вход и сократить удержание без изменения издержек."),
    "PROFIT_FACTOR_BELOW_GATE": ("LOCAL_PARAMETER_NEIGHBORHOOD", 2, "Проверить ближайшую область параметров при прежнем PASS."),
    "WALKFORWARD_FOLDS_UNSTABLE": ("REFINE_REGIME_CONTRACT", 1, "Разделить режимы рынка и проверить устойчивость фолдов."),
    "FINAL_HOLDOUT_FAILED": ("ORTHOGONAL_FUTURE_ONLY", 5, "Исключить прежний fingerprint и проверять только будущие данные."),
}


def gate_hash(gate_policy: dict) -> str:
    canonical = json.dumps(gate_policy, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    # PostgreSQL jsonb::text differs in whitespace, so DB stores its own md5 expression.
    return hashlib.sha256(canonical.encode()).hexdigest()


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
    return {"selection_folds": [1, 2, 3, 4], "trades": trades,
            "weighted_profit_factor": round(weighted_pf, 8),
            "weighted_expectancy": round(weighted_expectancy, 8),
            "folds_passed": sum(bool(item["passed"]) for item in development)}


def _number_set(value: float, ratios: tuple[float, ...], minimum: float, integer: bool = False) -> list:
    values = {max(minimum, value * ratio) for ratio in ratios}
    return sorted({int(round(item)) if integer else round(item, 4) for item in values})


def adapted_grid(base_grid: list[dict], reason: str) -> list[dict]:
    """Change hypotheses, never validation/OOS/walk-forward gates or cost inputs."""
    output: list[dict] = []
    for base in base_grid:
        clean = {key: value for key, value in base.items() if key not in {
            "commission", "slippage", "transaction_cost_bps", "adaptive_scenario_id"
        }}
        lookback, hold, threshold = int(clean["lookback"]), int(clean["hold"]), float(clean["threshold"])
        if reason == "INSUFFICIENT_TRADES":
            lookbacks, holds, thresholds = _number_set(lookback, (.5, .75, 1), 10, True), _number_set(hold, (.65, 1), 2, True), _number_set(threshold, (.65, .8, 1), 0)
        elif reason == "NEGATIVE_COST_ADJUSTED_EXPECTANCY":
            lookbacks, holds, thresholds = _number_set(lookback, (.75, 1, 1.25), 10, True), _number_set(hold, (.5, .75, 1), 2, True), _number_set(threshold, (1, 1.2, 1.5), 0)
        elif reason == "WALKFORWARD_FOLDS_UNSTABLE":
            lookbacks, holds, thresholds = _number_set(lookback, (.8, 1, 1.2), 10, True), [hold], _number_set(threshold, (.9, 1, 1.1), 0)
        elif reason == "FINAL_HOLDOUT_FAILED":
            lookbacks, holds, thresholds = _number_set(lookback, (.6, 1.4), 10, True), _number_set(hold, (.6, 1.4), 2, True), _number_set(threshold, (.75, 1.35), 0)
        else:
            lookbacks, holds, thresholds = _number_set(lookback, (.75, 1, 1.25), 10, True), _number_set(hold, (.75, 1, 1.25), 2, True), _number_set(threshold, (.9, 1, 1.15), 0)
        for lb, hd, th in itertools.product(lookbacks, holds, thresholds):
            candidate = {**clean, "lookback": lb, "hold": hd, "threshold": th}
            if candidate not in output:
                output.append(candidate)
            if len(output) >= MAX_VARIANTS_PER_ITEM:
                return output
    return output


def priority_score(row: dict) -> tuple:
    metrics = row["best_metrics"] or {}
    reason_rank = REASON_POLICY.get(row["primary_reason_code"], ("RESEARCH_NEW_FAMILY", 9, ""))[1]
    return (reason_rank, -int(metrics.get("folds", 0)), -float(metrics.get("profit_factor", 0)),
            -float(metrics.get("expectancy", 0)), row["algorithm_code"])


def activate_ready(cursor) -> int:
    cursor.execute("""
        UPDATE analytics.edge_search_adaptive_scenario_v1 s
        SET status_code='ACTIVE',reason_code='FUTURE_CONFIRMATION_WINDOW_READY',
            activated_at=clock_timestamp(),updated_at=clock_timestamp()
        WHERE s.status_code='WAITING_FUTURE_DATA'
          AND (SELECT count(*) FROM public.market_bars b WHERE b.symbol=s.target_symbol
               AND b.timeframe='M5' AND b.ts>s.confirmation_after_ts
               AND b.source NOT IN ('unknown','synthetic_futures_backfill_v1')) >= s.minimum_future_bars
        RETURNING adaptive_scenario_id
    """)
    ids = [str(row["adaptive_scenario_id"]) for row in cursor.fetchall()]
    if ids:
        cursor.execute("""UPDATE analytics.edge_next_research_plan_item_v1
            SET status_code='ACTIVE',updated_at=clock_timestamp()
            WHERE adaptive_scenario_id=ANY(%s::uuid[])""", (ids,))
    return len(ids)


def close_evaluated(cursor, search_run_id: str) -> int:
    cursor.execute("""
        WITH outcomes AS (
          SELECT s.adaptive_scenario_id,bool_or(w.verdict_code='OOS_PASS') AS passed
          FROM analytics.edge_search_adaptive_scenario_v1 s
          JOIN analytics.walkforward_edge_search_v3 w ON w.search_run_id=%s
           AND w.parameter_json->>'adaptive_scenario_id'=s.adaptive_scenario_id::text
          WHERE s.status_code='ACTIVE' GROUP BY s.adaptive_scenario_id
        ), changed AS (
          UPDATE analytics.edge_search_adaptive_scenario_v1 s
          SET status_code=CASE WHEN o.passed THEN 'EVALUATED_PASS' ELSE 'EVALUATED_FAIL' END,
              reason_code=CASE WHEN o.passed THEN 'FUTURE_DATA_PASS' ELSE 'FUTURE_DATA_NO_PASS' END,
              evaluated_at=clock_timestamp(),updated_at=clock_timestamp()
          FROM outcomes o WHERE s.adaptive_scenario_id=o.adaptive_scenario_id
          RETURNING s.adaptive_scenario_id,s.status_code
        )
        UPDATE analytics.edge_next_research_plan_item_v1 i
        SET status_code=c.status_code,updated_at=clock_timestamp()
        FROM changed c WHERE i.adaptive_scenario_id=c.adaptive_scenario_id
        RETURNING i.plan_item_id
    """, (search_run_id,))
    return len(cursor.fetchall())


def sync_plan_statuses(cursor) -> None:
    cursor.execute("""
        UPDATE analytics.edge_next_research_plan_v1 p SET
          status_code=CASE
            WHEN NOT EXISTS (SELECT 1 FROM analytics.edge_next_research_plan_item_v1 i WHERE i.plan_id=p.plan_id) THEN 'EMPTY'
            WHEN EXISTS (SELECT 1 FROM analytics.edge_next_research_plan_item_v1 i WHERE i.plan_id=p.plan_id AND i.status_code='ACTIVE') THEN 'ACTIVE'
            WHEN NOT EXISTS (SELECT 1 FROM analytics.edge_next_research_plan_item_v1 i WHERE i.plan_id=p.plan_id AND i.status_code IN ('WAITING_FUTURE_DATA','ACTIVE')) THEN 'EVALUATED'
            ELSE 'WAITING_FUTURE_DATA' END,
          updated_at=clock_timestamp()
        WHERE p.status_code <> 'EMPTY'
    """)


def main() -> None:
    parent_run_id = os.environ["EDGE_SEARCH_SCENARIO_RUN_ID"]
    search_run_id = os.environ["EDGE_SEARCH_WALKFORWARD_RUN_ID"]
    plan_id = uuid.uuid5(NAMESPACE, f"{parent_run_id}:{VERSION}")
    created = 0
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            evaluated = close_evaluated(cursor, search_run_id)
            activated = activate_ready(cursor)
            cursor.execute("""
                SELECT a.*,r.strategy_code,r.parameter_grid,r.regime_policy,r.gate_policy,
                       w.result_id,w.symbol,w.parameter_json,w.fold_metrics
                FROM analytics.edge_search_algorithm_analysis_v1 a
                JOIN analytics.edge_search_algorithm_registry_v1 r USING (algorithm_code)
                JOIN LATERAL (
                  SELECT x.* FROM analytics.walkforward_edge_search_v3 x
                  WHERE x.search_run_id=a.search_run_id AND x.strategy_family=a.algorithm_code
                    AND x.verdict_code='OOS_FAIL'
                  ORDER BY x.folds_passed DESC,x.net_profit_factor DESC,x.net_expectancy DESC,x.result_id
                  LIMIT 1
                ) w ON true
                WHERE a.run_id=%s AND a.verdict_code='FAIL' AND r.enabled
            """, (parent_run_id,))
            failures = sorted(cursor.fetchall(), key=priority_score)
            reason_summary = dict(Counter(row["primary_reason_code"] for row in failures))
            cursor.execute("""
                INSERT INTO analytics.edge_next_research_plan_v1
                  (plan_id,parent_run_id,parent_search_run_id,generator_version,status_code,source_failures,reason_summary)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (parent_run_id,generator_version) DO NOTHING
            """, (str(plan_id),parent_run_id,search_run_id,VERSION,
                  "WAITING_FUTURE_DATA" if failures else "EMPTY",len(failures),psycopg2.extras.Json(reason_summary)))
            for priority, row in enumerate(failures[:MAX_NEW_SCENARIOS], 1):
                adaptation, _, rationale = REASON_POLICY.get(row["primary_reason_code"],
                    ("RESEARCH_NEW_FAMILY", 9, "Сформировать новую проверяемую гипотезу."))
                grid = adapted_grid(row["parameter_grid"], row["primary_reason_code"])
                fold5 = next(item for item in row["fold_metrics"] if int(item["fold"]) == 5)
                plan_item_id = uuid.uuid5(NAMESPACE, f"{plan_id}:{row['algorithm_code']}")
                scenario_id = uuid.uuid5(NAMESPACE, f"{plan_item_id}:adaptive")
                metrics = development_metrics(row["fold_metrics"]) or {}
                policy = {"generator": VERSION, "plan_id": str(plan_id), "plan_item_id": str(plan_item_id),
                          "priority": priority, "adaptation_code": adaptation,
                          "gate_policy": row["gate_policy"], "selection_uses_final_holdout": False}
                holdout = {"selection_folds": [1, 2, 3, 4], "consumed_holdout_fold": 5,
                           "confirmation_mode": "FUTURE_DATA_ONLY", "confirmation_after": fold5["end"]}
                cursor.execute("""
                    INSERT INTO analytics.edge_search_adaptive_scenario_v1
                      (adaptive_scenario_id,parent_run_id,parent_search_run_id,parent_result_id,
                       algorithm_code,strategy_code,target_symbol,parameter_grid,selection_metrics,
                       generation_policy,holdout_policy,confirmation_after_ts,minimum_future_bars,
                       status_code,reason_code,config_version)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                            'WAITING_FUTURE_DATA','FAIL_DRIVEN_PLAN_WAITING_FUTURE_DATA',%s)
                    ON CONFLICT (parent_result_id,config_version) DO NOTHING
                """, (str(scenario_id),parent_run_id,search_run_id,str(row["result_id"]),row["algorithm_code"],
                      row["strategy_code"],row["symbol"],psycopg2.extras.Json(grid),psycopg2.extras.Json(metrics),
                      psycopg2.extras.Json(policy),psycopg2.extras.Json(holdout),datetime.fromisoformat(fold5["end"]),
                      MIN_FUTURE_BARS,VERSION))
                cursor.execute("""
                    INSERT INTO analytics.edge_next_research_plan_item_v1
                      (plan_item_id,plan_id,priority,algorithm_code,strategy_code,primary_reason_code,
                       adaptation_code,parameter_grid,regime_policy,pass_gate_snapshot,pass_gate_hash,
                       evaluation_budget,source_result_id,adaptive_scenario_id,status_code,rationale_ru)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,md5(%s::jsonb::text),%s,%s,%s,
                            'WAITING_FUTURE_DATA',%s)
                    ON CONFLICT (plan_id,algorithm_code) DO NOTHING
                """, (str(plan_item_id),str(plan_id),priority,row["algorithm_code"],row["strategy_code"],
                      row["primary_reason_code"],adaptation,psycopg2.extras.Json(grid),
                      psycopg2.extras.Json(row["regime_policy"]),psycopg2.extras.Json(row["gate_policy"]),
                      json.dumps(row["gate_policy"]),len(grid),str(row["result_id"]),str(scenario_id),rationale))
                created += cursor.rowcount
            cursor.execute("""UPDATE analytics.edge_next_research_plan_v1 SET
                item_count=(SELECT count(*) FROM analytics.edge_next_research_plan_item_v1 WHERE plan_id=%s),
                total_parameter_variants=coalesce((SELECT sum(evaluation_budget) FROM analytics.edge_next_research_plan_item_v1 WHERE plan_id=%s),0),
                updated_at=clock_timestamp() WHERE plan_id=%s""", (str(plan_id),str(plan_id),str(plan_id)))
            sync_plan_statuses(cursor)
    print(f"next_research_plan_id={plan_id}")
    print(f"next_research_plan_items_created={created}")
    print(f"adaptive_scenarios_activated={activated}")
    print(f"adaptive_scenarios_evaluated={evaluated}")
    print("pass_gates=UNCHANGED")
    print("confirmation_mode=FUTURE_DATA_ONLY")
    print("VERDICT=NEXT_EDGE_RESEARCH_PLAN_READY")


if __name__ == "__main__":
    main()
