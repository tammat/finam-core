from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime

import psycopg2
import psycopg2.extras

from scripts.generate_adaptive_edge_search_scenarios_v1 import adapted_grid


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
VERSION = "OOS_REMEDIATION_BRANCHES_V2_FOCUSED_ENTRY_EXIT"
NAMESPACE = uuid.UUID("4e589952-d68d-4b29-a1cf-f10f6fd80da8")
MIN_FUTURE_BARS = int(os.getenv("OOS_REMEDIATION_MIN_FUTURE_BARS", "500"))
BRANCH_POLICY = {
    "COST_REMEDIATION": {"reason": "NEGATIVE_COST_ADJUSTED_EXPECTANCY", "sources": 4, "budget": 34},
    "SAMPLE_EXPANSION": {"reason": "INSUFFICIENT_TRADES", "sources": 2, "budget": 10},
}
FOCUS_ALGORITHM_BUDGET = {
    "DONCHIAN_VOL_BREAKOUT": 20,
    "EMA_TREND": 14,
}


def fingerprint(algorithm: str, symbol: str, params: dict) -> str:
    clean = {k: v for k, v in params.items() if k != "adaptive_scenario_id"}
    raw = json.dumps([algorithm, symbol, clean], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def latest_cohort(cursor) -> dict | None:
    cursor.execute("""
      SELECT scenario_run_id,search_run_id,count(*) AS evaluations
      FROM analytics.edge_methodology_evaluation_v1
      GROUP BY scenario_run_id,search_run_id
      HAVING count(*) >= 100
      ORDER BY max(created_at) DESC LIMIT 1
    """)
    return cursor.fetchone()


def source_rows(cursor, search_run_id: str) -> list[dict]:
    cursor.execute("""
      SELECT w.result_id,w.strategy_family AS algorithm_code,r.strategy_code,w.symbol,
             w.parameter_json,w.fold_metrics,w.folds_passed,w.net_profit_factor,
             w.net_expectancy,w.total_trades,w.reason_code,r.gate_policy,
             coalesce(p.priority_rank,100) priority_rank
      FROM analytics.walkforward_edge_search_v3 w
      JOIN analytics.edge_search_algorithm_registry_v1 r ON r.algorithm_code=w.strategy_family
      LEFT JOIN analytics.edge_algorithm_compute_policy_v1 p ON p.algorithm_code=w.strategy_family
      WHERE w.search_run_id=%s AND w.reason_code IN
        ('NEGATIVE_COST_ADJUSTED_EXPECTANCY','INSUFFICIENT_TRADES')
        AND r.enabled AND NOT coalesce(p.promotion_blocked,false)
        AND w.parameter_json ? 'lookback' AND w.parameter_json ? 'hold'
        AND w.parameter_json ? 'threshold'
      ORDER BY CASE w.reason_code WHEN 'NEGATIVE_COST_ADJUSTED_EXPECTANCY' THEN 1 ELSE 2 END,
        coalesce(p.priority_rank,100),
        w.folds_passed DESC,
        CASE WHEN w.net_profit_factor BETWEEN 0 AND 10 THEN w.net_profit_factor ELSE 0 END DESC,
        w.net_expectancy DESC,w.total_trades DESC,w.result_id
    """, (search_run_id,))
    rows = [dict(row) for row in cursor.fetchall()]
    selected: list[dict] = []
    for branch, policy in BRANCH_POLICY.items():
        seen: set[tuple[str, str]] = set()
        focus_seen: set[str] = set()
        for row in rows:
            if row["reason_code"] != policy["reason"]:
                continue
            if branch == "COST_REMEDIATION":
                algorithm = str(row["algorithm_code"])
                if algorithm not in FOCUS_ALGORITHM_BUDGET or algorithm in focus_seen:
                    continue
                focus_seen.add(algorithm)
            key = (str(row["algorithm_code"]), str(row["symbol"]))
            if key in seen:
                continue
            row["branch_code"] = branch
            selected.append(row)
            seen.add(key)
            if branch == "COST_REMEDIATION" and len(focus_seen) >= len(FOCUS_ALGORITHM_BUDGET):
                break
            if branch != "COST_REMEDIATION" and len(seen) >= policy["sources"]:
                break
    return selected


def fold_end(row: dict) -> datetime:
    folds = list(row.get("fold_metrics") or [])
    selected = next((item for item in folds if int(item.get("fold", 0)) == 5), folds[-1] if folds else None)
    if not selected or not selected.get("end"):
        raise RuntimeError(f"OOS_REMEDIATION_FOLD_END_MISSING:{row['result_id']}")
    return datetime.fromisoformat(str(selected["end"]).replace("Z", "+00:00"))


def future_ready(cursor, symbol: str, after: datetime) -> bool:
    cursor.execute("""
      SELECT count(*) >= %s AS ready FROM public.market_bars
      WHERE symbol=%s AND timeframe='M5' AND ts>%s
        AND source NOT IN ('unknown','synthetic_futures_backfill_v1')
    """, (MIN_FUTURE_BARS, symbol, after))
    return bool(cursor.fetchone()["ready"])


def reconcile(cursor) -> None:
    cursor.execute("""
      UPDATE analytics.edge_search_adaptive_scenario_v1 s
      SET status_code='ACTIVE',reason_code='FUTURE_CONFIRMATION_WINDOW_READY',
          activated_at=coalesce(activated_at,clock_timestamp()),updated_at=clock_timestamp()
      WHERE s.config_version LIKE %s AND s.status_code='WAITING_FUTURE_DATA'
        AND (SELECT count(*) FROM public.market_bars b WHERE b.symbol=s.target_symbol
             AND b.timeframe='M5' AND b.ts>s.confirmation_after_ts
             AND b.source NOT IN ('unknown','synthetic_futures_backfill_v1')) >= s.minimum_future_bars
    """, (VERSION + "%",))
    cursor.execute("""
      UPDATE analytics.oos_remediation_candidate_v1 c
      SET status_code='QUEUED',reason_code='ADAPTIVE_SCENARIO_ACTIVE',updated_at=clock_timestamp()
      FROM analytics.edge_search_adaptive_scenario_v1 s
      WHERE c.adaptive_scenario_id=s.adaptive_scenario_id
        AND c.status_code='WAITING_FUTURE_DATA' AND s.status_code='ACTIVE'
    """)


def enforce_policy_budgets(cursor, process_id: str) -> None:
    for branch, policy in BRANCH_POLICY.items():
        cursor.execute("""
          WITH ranked AS (
            SELECT candidate_id,row_number() OVER(ORDER BY generated_at,candidate_id) AS position
            FROM analytics.oos_remediation_candidate_v1
            WHERE process_id=%s AND branch_code=%s
              AND status_code IN ('WAITING_FUTURE_DATA','QUEUED')
          )
          UPDATE analytics.oos_remediation_candidate_v1 c
          SET status_code='PRUNED_BUDGET',reason_code='RESOURCE_ALLOCATION_70_20_10',
              updated_at=clock_timestamp()
          FROM ranked r WHERE c.candidate_id=r.candidate_id AND r.position>%s
        """, (process_id, branch, int(policy["budget"])))
    cursor.execute("""
      WITH kept AS (
        SELECT adaptive_scenario_id,jsonb_agg(parameter_json ORDER BY fingerprint) parameter_grid
        FROM analytics.oos_remediation_candidate_v1
        WHERE process_id=%s AND adaptive_scenario_id IS NOT NULL
          AND status_code NOT LIKE 'PRUNED_%%'
        GROUP BY adaptive_scenario_id
      )
      UPDATE analytics.edge_search_adaptive_scenario_v1 s
      SET parameter_grid=k.parameter_grid,updated_at=clock_timestamp()
      FROM kept k WHERE s.adaptive_scenario_id=k.adaptive_scenario_id
    """, (process_id,))
    cursor.execute("""
      WITH outcome AS (
        SELECT c.candidate_id,bool_or(w.verdict_code='OOS_PASS') passed
        FROM analytics.oos_remediation_candidate_v1 c
        JOIN analytics.walkforward_edge_search_v3 w
          ON w.strategy_family=c.algorithm_code AND w.symbol=c.symbol
         AND (w.parameter_json-'adaptive_scenario_id')=c.parameter_json
         AND w.parameter_json->>'adaptive_scenario_id'=c.adaptive_scenario_id::text
        WHERE c.status_code IN ('QUEUED','WAITING_FUTURE_DATA')
        GROUP BY c.candidate_id
      )
      UPDATE analytics.oos_remediation_candidate_v1 c SET
        status_code=CASE WHEN o.passed THEN 'OOS_PASS' ELSE 'EVALUATED_FAIL' END,
        reason_code=CASE WHEN o.passed THEN 'UNCHANGED_GATES_PASS' ELSE 'UNCHANGED_GATES_FAIL' END,
        evaluated_at=clock_timestamp(),updated_at=clock_timestamp()
      FROM outcome o WHERE c.candidate_id=o.candidate_id
    """)
    cursor.execute("""
      WITH outcome AS (
        SELECT adaptive_scenario_id,bool_or(status_code='OOS_PASS') passed
        FROM analytics.oos_remediation_candidate_v1
        WHERE adaptive_scenario_id IS NOT NULL AND status_code IN ('EVALUATED_FAIL','OOS_PASS')
        GROUP BY adaptive_scenario_id
      )
      UPDATE analytics.edge_search_adaptive_scenario_v1 s SET
        status_code=CASE WHEN o.passed THEN 'EVALUATED_PASS' ELSE 'EVALUATED_FAIL' END,
        reason_code=CASE WHEN o.passed THEN 'FUTURE_DATA_PASS' ELSE 'FUTURE_DATA_NO_PASS' END,
        evaluated_at=clock_timestamp(),updated_at=clock_timestamp()
      FROM outcome o WHERE s.adaptive_scenario_id=o.adaptive_scenario_id
        AND s.status_code='ACTIVE'
    """)


def update_process(cursor, process_id: str) -> None:
    cursor.execute("""
      SELECT count(*) total,
        count(*) FILTER(WHERE status_code LIKE 'PRUNED_%%') pruned,
        count(*) FILTER(WHERE status_code IN ('EVALUATED_FAIL','OOS_PASS')) evaluated,
        count(*) FILTER(WHERE status_code IN ('WAITING_FUTURE_DATA','QUEUED')) active
      FROM analytics.oos_remediation_candidate_v1 WHERE process_id=%s
    """, (process_id,))
    stats = cursor.fetchone()
    total, done = int(stats["total"] or 0), int(stats["pruned"] or 0) + int(stats["evaluated"] or 0)
    complete = total > 0 and done == total
    progress = round(100.0 * done / total, 2) if total else 0.0
    cursor.execute("""
      UPDATE analytics.oos_remediation_process_v1 SET
        status_code=%s,current_step_code=%s,progress_pct=%s,
        finished_at=CASE WHEN %s THEN coalesce(finished_at,clock_timestamp()) ELSE NULL END,
        updated_at=clock_timestamp() WHERE process_id=%s
    """, ("COMPLETE" if complete else "MONITORING",
          "OOS_RESULTS_READY" if complete else "WAITING_OOS_EVALUATION", progress, complete, process_id))


def main() -> int:
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cohort = latest_cohort(cursor)
            if not cohort:
                print("VERDICT=NO_FULL_METHODOLOGY_COHORT")
                return 0
            process_id = str(uuid.uuid5(NAMESPACE, f"{cohort['search_run_id']}:{VERSION}"))
            cursor.execute("""
              INSERT INTO analytics.oos_remediation_process_v1(
                process_id,parent_scenario_run_id,parent_search_run_id,status_code,current_step_code,
                source_failures,config_version)
              VALUES(%s,%s,%s,'GENERATING','READING_FAIL_REASONS',%s,%s)
              ON CONFLICT(parent_search_run_id,config_version) DO UPDATE SET updated_at=clock_timestamp()
            """, (process_id, str(cohort["scenario_run_id"]), str(cohort["search_run_id"]),
                  int(cohort["evaluations"]), VERSION))
            reconcile(cursor)
            enforce_policy_budgets(cursor, process_id)
            existing_global: set[str] = set()
            cursor.execute("""SELECT fingerprint FROM analytics.oos_remediation_candidate_v1
                               WHERE process_id<>%s AND status_code NOT LIKE 'PRUNED_%%'""", (process_id,))
            existing_global.update(str(row["fingerprint"]) for row in cursor.fetchall())
            accepted = {branch: 0 for branch in BRANCH_POLICY}
            accepted_by_algorithm = {algorithm: 0 for algorithm in FOCUS_ALGORITHM_BUDGET}
            for row in source_rows(cursor, str(cohort["search_run_id"])):
                branch = row["branch_code"]
                algorithm = str(row["algorithm_code"])
                algorithm_budget = (
                    FOCUS_ALGORITHM_BUDGET.get(algorithm, BRANCH_POLICY[branch]["budget"])
                    if branch == "COST_REMEDIATION" else BRANCH_POLICY[branch]["budget"]
                )
                generated = adapted_grid([dict(row["parameter_json"])], str(row["reason_code"]),
                                         algorithm, algorithm_budget)
                scenario_id = str(uuid.uuid5(NAMESPACE, f"{process_id}:{branch}:{row['result_id']}"))
                accepted_params: list[dict] = []
                candidates: list[tuple[dict, str, str, str]] = []
                local_seen: set[str] = set()
                for params in generated:
                    clean = {k: v for k, v in params.items() if k != "adaptive_scenario_id"}
                    fp = fingerprint(str(row["algorithm_code"]), str(row["symbol"]), clean)
                    if fp in local_seen or fp in existing_global:
                        status, reason = "PRUNED_DUPLICATE", "DUPLICATE_FINGERPRINT"
                    elif accepted[branch] >= BRANCH_POLICY[branch]["budget"] or (
                        branch == "COST_REMEDIATION"
                        and accepted_by_algorithm[algorithm] >= algorithm_budget
                    ):
                        status, reason = "PRUNED_BUDGET", "SAFE_COMPUTE_BUDGET"
                    else:
                        status, reason = "GENERATED", str(row["reason_code"])
                        accepted[branch] += 1
                        if branch == "COST_REMEDIATION":
                            accepted_by_algorithm[algorithm] += 1
                        accepted_params.append(clean)
                        existing_global.add(fp)
                    local_seen.add(fp)
                    candidates.append((clean, fp, status, reason))
                if accepted_params:
                    after = fold_end(row)
                    ready = future_ready(cursor, str(row["symbol"]), after)
                    scenario_status = "ACTIVE" if ready else "WAITING_FUTURE_DATA"
                    policy = {"generator": VERSION, "branch_code": branch,
                              "gate_policy": row["gate_policy"], "selection_uses_final_holdout": False,
                              "cost_model_unchanged": True, "process_id": process_id}
                    holdout = {"selection_folds": [1, 2, 3, 4], "consumed_holdout_fold": 5,
                               "confirmation_mode": "FUTURE_DATA_ONLY", "confirmation_after": after.isoformat()}
                    cursor.execute("""
                      INSERT INTO analytics.edge_search_adaptive_scenario_v1(
                        adaptive_scenario_id,parent_run_id,parent_search_run_id,parent_result_id,
                        algorithm_code,strategy_code,target_symbol,parameter_grid,selection_metrics,
                        generation_policy,holdout_policy,confirmation_after_ts,minimum_future_bars,
                        status_code,reason_code,config_version)
                      VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'{}'::jsonb,%s,%s,%s,%s,%s,%s,%s)
                      ON CONFLICT(parent_result_id,config_version) DO UPDATE SET
                        parameter_grid=excluded.parameter_grid,generation_policy=excluded.generation_policy,
                        updated_at=clock_timestamp()
                    """, (scenario_id, str(cohort["scenario_run_id"]), str(cohort["search_run_id"]),
                          str(row["result_id"]), str(row["algorithm_code"]), str(row["strategy_code"]),
                          str(row["symbol"]), psycopg2.extras.Json(accepted_params),
                          psycopg2.extras.Json(policy), psycopg2.extras.Json(holdout), after,
                          MIN_FUTURE_BARS, scenario_status,
                          "READY_FOR_SYSTEM_CYCLE" if ready else "WAITING_FUTURE_DATA", f"{VERSION}:{branch}"))
                else:
                    scenario_status = "GENERATED"
                accepted_fps = {fingerprint(str(row["algorithm_code"]), str(row["symbol"]), p)
                                for p in accepted_params}
                for params, fp, status, reason in candidates:
                    if status == "GENERATED":
                        status = "QUEUED" if scenario_status == "ACTIVE" else "WAITING_FUTURE_DATA"
                    candidate_id = str(uuid.uuid5(NAMESPACE, f"{process_id}:{branch}:{fp}"))
                    cursor.execute("""
                      INSERT INTO analytics.oos_remediation_candidate_v1(
                        candidate_id,process_id,branch_code,parent_result_id,adaptive_scenario_id,
                        algorithm_code,strategy_code,symbol,parameter_json,fingerprint,status_code,reason_code)
                      VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                      ON CONFLICT(process_id,branch_code,fingerprint) DO NOTHING
                    """, (candidate_id, process_id, branch, str(row["result_id"]),
                          scenario_id if fp in accepted_fps else None, str(row["algorithm_code"]),
                          str(row["strategy_code"]), str(row["symbol"]), psycopg2.extras.Json(params),
                          fp, status, reason))
            enforce_policy_budgets(cursor, process_id)
            update_process(cursor, process_id)
            cursor.execute("""
              SELECT branch_code,count(*) created,
                count(*) FILTER(WHERE status_code LIKE 'PRUNED_%%') pruned,
                count(*) FILTER(WHERE status_code='OOS_PASS') passed
              FROM analytics.oos_remediation_candidate_v1 WHERE process_id=%s GROUP BY branch_code ORDER BY branch_code
            """, (process_id,))
            for row in cursor.fetchall():
                print(f"branch={row['branch_code']} created={row['created']} pruned={row['pruned']} oos_pass={row['passed']}")
    print("pass_gates=UNCHANGED")
    print("VERDICT=OOS_REMEDIATION_BRANCHES_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
