from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
VERSION = "TEMPORAL_OOS_BRANCHES_V1"
NAMESPACE = uuid.UUID("c0f47bea-e092-4a9d-b1a1-9937ce101b3f")
NON_HYPOTHESIS_KEYS = {
    "adaptive_scenario_id", "commission", "slippage", "transaction_cost_bps",
    "execution_policy",
}


def fingerprint(algorithm: str, symbol: str, parameters: dict) -> str:
    clean = {key: value for key, value in parameters.items() if key != "adaptive_scenario_id"}
    payload = json.dumps([algorithm, symbol, clean], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def temporal_parameters(base: dict, overlay: dict, session_code: str) -> dict:
    parameters = {key: value for key, value in base.items() if key not in NON_HYPOTHESIS_KEYS}
    parameters.update(overlay)
    parameters.update({
        "entry_session_mode": "REQUIRE",
        "entry_allowed_sessions": [session_code],
        "session_analysis": "MARKET_SESSION_CONTRACT_V1",
    })
    return parameters


def fold_end(row: dict) -> datetime:
    folds = list(row.get("fold_metrics") or [])
    selected = next((item for item in folds if int(item.get("fold", 0)) == 5), folds[-1] if folds else None)
    if not selected or not selected.get("end"):
        raise RuntimeError(f"TEMPORAL_OOS_FOLD_END_MISSING:{row['result_id']}")
    return datetime.fromisoformat(str(selected["end"]).replace("Z", "+00:00"))


def latest_cohort(cursor) -> dict | None:
    cursor.execute("""
      SELECT scenario_run_id,search_run_id,count(*) evaluations
      FROM analytics.edge_methodology_evaluation_v1
      GROUP BY scenario_run_id,search_run_id HAVING count(*)>=100
      ORDER BY max(created_at) DESC LIMIT 1
    """)
    return cursor.fetchone()


def source_rows(cursor, search_run_id: str) -> list[dict]:
    cursor.execute("""
      WITH ranked AS (
        SELECT w.*,r.strategy_code,r.gate_policy,a.parameter_overlay,a.priority,
               row_number() OVER(PARTITION BY w.strategy_family ORDER BY
                 (w.total_trades>=80) DESC,w.folds_passed DESC,
                 CASE WHEN w.net_profit_factor BETWEEN 0 AND 10 THEN w.net_profit_factor ELSE 0 END DESC,
                 w.total_trades DESC,w.result_id) source_rank
        FROM analytics.walkforward_edge_search_v3 w
        JOIN analytics.edge_search_algorithm_registry_v1 r
          ON r.algorithm_code=w.strategy_family AND r.enabled
        JOIN analytics.temporal_oos_algorithm_policy_v1 a
          ON a.algorithm_code=w.strategy_family AND a.enabled
        WHERE w.search_run_id=%s
          AND analytics.oos_variant_admission_reason_v1(
                w.symbol,w.timeframe,w.parameter_json
              )='ELIGIBLE'
          AND EXISTS (
              SELECT 1
              FROM analytics.market_microstructure_snapshot_v1 m
              WHERE m.symbol=w.symbol
                AND m.observed_at >= clock_timestamp()-interval '15 minutes'
                AND m.bid_levels>0 AND m.ask_levels>0
                AND m.bid_depth>0 AND m.ask_depth>0
          )
      ) SELECT * FROM ranked WHERE source_rank=1 ORDER BY priority,strategy_family
    """, (search_run_id,))
    return [dict(row) for row in cursor.fetchall()]


def future_bars(cursor, symbol: str, after: datetime) -> int:
    cursor.execute("""
      SELECT count(*) FROM public.market_bars
      WHERE symbol=%s AND timeframe='M5' AND ts>%s
        AND source NOT IN ('unknown','synthetic_futures_backfill_v1')
    """, (symbol, after))
    return int(cursor.fetchone()["count"])


def update_process(cursor, process_id: str) -> None:
    cursor.execute("""
      WITH stats AS (
        SELECT count(*) total,
          count(*) FILTER(WHERE status_code IN ('EVALUATED_FAIL','OOS_PASS')) done,
          count(*) FILTER(WHERE status_code IN ('WAITING_FUTURE_DATA','QUEUED')) active
        FROM analytics.oos_remediation_candidate_v1
        WHERE process_id=%s AND branch_code='TEMPORAL_SESSION'
      ) UPDATE analytics.oos_remediation_process_v1 p SET
        status_code=CASE WHEN s.active=0 AND s.total>0 THEN 'COMPLETE' ELSE 'MONITORING' END,
        current_step_code=CASE WHEN s.active=0 AND s.total>0 THEN 'OOS_RESULTS_READY'
                               ELSE 'WAITING_TEMPORAL_OOS' END,
        progress_pct=round(100.0*s.done/greatest(1,s.total),2),
        finished_at=CASE WHEN s.active=0 AND s.total>0 THEN coalesce(p.finished_at,clock_timestamp()) ELSE NULL END,
        updated_at=clock_timestamp()
      FROM stats s WHERE p.process_id=%s
    """, (process_id, process_id))


def main() -> int:
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cohort = latest_cohort(cursor)
            if not cohort:
                print("VERDICT=NO_METHODOLOGY_COHORT")
                return 0
            # Планировщик вызывает этот генератор часто. Уже созданный
            # future-only процесс не требует повторного тяжёлого ранжирования
            # всей walk-forward таблицы: ему достаточно обновить прогресс.
            cursor.execute("""
              SELECT process_id FROM analytics.oos_remediation_process_v1
              WHERE parent_search_run_id=%s AND config_version=%s
                AND status_code IN ('GENERATING','MONITORING')
              ORDER BY updated_at DESC LIMIT 1
            """, (str(cohort["search_run_id"]), VERSION))
            existing = cursor.fetchone()
            if existing:
                update_process(cursor, str(existing["process_id"]))
                print("VERDICT=TEMPORAL_OOS_PROCESS_MONITORED")
                return 0
            sources = source_rows(cursor, str(cohort["search_run_id"]))
            if not sources:
                print("VERDICT=NO_TEMPORAL_SOURCE_RESULTS")
                return 0
            cursor.execute("""
              SELECT session_code,title_ru,priority,minimum_future_bars,config_version
              FROM analytics.temporal_oos_session_policy_v1 WHERE enabled
              ORDER BY priority,session_code
            """)
            sessions = [dict(row) for row in cursor.fetchall()]
            process_id = str(uuid.uuid5(NAMESPACE, f"{cohort['search_run_id']}:{VERSION}"))
            cursor.execute("""
              INSERT INTO analytics.oos_remediation_process_v1(
                process_id,parent_scenario_run_id,parent_search_run_id,status_code,current_step_code,
                source_failures,config_version)
              VALUES(%s,%s,%s,'GENERATING','GENERATING_TEMPORAL_BRANCHES',%s,%s)
              ON CONFLICT(parent_search_run_id,config_version) DO UPDATE SET updated_at=clock_timestamp()
            """, (process_id, str(cohort["scenario_run_id"]), str(cohort["search_run_id"]),
                  len(sources), VERSION))
            created = queued = waiting = 0
            for source in sources:
                confirmation_after = fold_end(source)
                base = dict(source["parameter_json"])
                overlay = dict(source["parameter_overlay"])
                for session in sessions:
                    session_code = str(session["session_code"])
                    parameters = temporal_parameters(base, overlay, session_code)
                    scenario_version = f"{VERSION}:{source['strategy_family']}:{session_code}"
                    scenario_id = str(uuid.uuid5(
                        NAMESPACE, f"{source['result_id']}:{scenario_version}"
                    ))
                    # Только M5 future-only данные; M1 сознательно не входит в
                    # этот контур, пока не появится отдельный execution contract.
                    bars = future_bars(cursor, str(source["symbol"]), confirmation_after)
                    ready = bars >= int(session["minimum_future_bars"])
                    scenario_status = "ACTIVE" if ready else "WAITING_FUTURE_DATA"
                    cursor.execute("""
                      INSERT INTO analytics.edge_search_adaptive_scenario_v1(
                        adaptive_scenario_id,parent_run_id,parent_search_run_id,parent_result_id,
                        algorithm_code,strategy_code,target_symbol,parameter_grid,selection_metrics,
                        generation_policy,holdout_policy,confirmation_after_ts,minimum_future_bars,
                        status_code,reason_code,config_version,activated_at)
                      VALUES(%s,%s,%s,%s,%s,%s,%s,%s,'{}'::jsonb,%s,%s,%s,%s,%s,%s,%s,
                             CASE WHEN %s THEN clock_timestamp() END)
                      ON CONFLICT(parent_result_id,config_version) DO UPDATE SET
                        parameter_grid=excluded.parameter_grid,
                        status_code=CASE
                          WHEN analytics.edge_search_adaptive_scenario_v1.status_code='WAITING_FUTURE_DATA'
                            THEN excluded.status_code
                          ELSE analytics.edge_search_adaptive_scenario_v1.status_code END,
                        reason_code=CASE
                          WHEN analytics.edge_search_adaptive_scenario_v1.status_code='WAITING_FUTURE_DATA'
                            THEN excluded.reason_code
                          ELSE analytics.edge_search_adaptive_scenario_v1.reason_code END,
                        activated_at=CASE WHEN excluded.status_code='ACTIVE'
                          THEN coalesce(analytics.edge_search_adaptive_scenario_v1.activated_at,clock_timestamp())
                          ELSE analytics.edge_search_adaptive_scenario_v1.activated_at END,
                        updated_at=clock_timestamp()
                    """, (scenario_id, str(cohort["scenario_run_id"]), str(cohort["search_run_id"]),
                          str(source["result_id"]), str(source["strategy_family"]),
                          str(source["strategy_code"]), str(source["symbol"]),
                          psycopg2.extras.Json([parameters]),
                          psycopg2.extras.Json({
                              "generator": VERSION, "branch_code": "TEMPORAL_SESSION",
                              "session_code": session_code, "session_policy_version": session["config_version"],
                              "gate_policy": source["gate_policy"], "pass_gates_unchanged": True,
                              "cost_model_unchanged": True, "future_only": True,
                              "selection_uses_final_holdout": False,
                          }),
                          psycopg2.extras.Json({
                              "selection_folds": [1, 2, 3, 4], "consumed_holdout_fold": 5,
                              "fold_overlap_forbidden": True, "confirmation_mode": "FUTURE_DATA_ONLY",
                              "confirmation_after": confirmation_after.isoformat(),
                          }), confirmation_after, int(session["minimum_future_bars"]),
                          scenario_status, "TEMPORAL_OOS_READY" if ready else "WAITING_FUTURE_DATA",
                          scenario_version, ready))
                    fp = fingerprint(str(source["strategy_family"]), str(source["symbol"]), parameters)
                    candidate_id = str(uuid.uuid5(NAMESPACE, f"{process_id}:{session_code}:{fp}"))
                    candidate_status = "QUEUED" if ready else "WAITING_FUTURE_DATA"
                    cursor.execute("""
                      INSERT INTO analytics.oos_remediation_candidate_v1(
                        candidate_id,process_id,branch_code,parent_result_id,adaptive_scenario_id,
                        algorithm_code,strategy_code,symbol,parameter_json,fingerprint,status_code,reason_code)
                      VALUES(%s,%s,'TEMPORAL_SESSION',%s,%s,%s,%s,%s,%s,%s,%s,%s)
                      ON CONFLICT(process_id,branch_code,fingerprint) DO UPDATE SET
                        status_code=CASE
                          WHEN analytics.oos_remediation_candidate_v1.status_code='WAITING_FUTURE_DATA'
                            THEN excluded.status_code
                          ELSE analytics.oos_remediation_candidate_v1.status_code END,
                        reason_code=CASE
                          WHEN analytics.oos_remediation_candidate_v1.status_code='WAITING_FUTURE_DATA'
                            THEN excluded.reason_code
                          ELSE analytics.oos_remediation_candidate_v1.reason_code END,
                        updated_at=clock_timestamp()
                    """, (candidate_id, process_id, str(source["result_id"]), scenario_id,
                          str(source["strategy_family"]), str(source["strategy_code"]),
                          str(source["symbol"]), psycopg2.extras.Json(parameters), fp,
                          candidate_status, "TEMPORAL_OOS_READY" if ready else "WAITING_FUTURE_DATA"))
                    created += 1
                    queued += int(ready)
                    waiting += int(not ready)
            update_process(cursor, process_id)
    print(f"temporal_variants={created}")
    print(f"queued={queued}")
    print(f"waiting_future_data={waiting}")
    print("pass_gates=UNCHANGED")
    print("VERDICT=TEMPORAL_OOS_BRANCHES_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
