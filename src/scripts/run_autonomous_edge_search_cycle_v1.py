from __future__ import annotations

import os
import re
import subprocess
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg2


ROOT = Path("/opt/finam-core")
PYTHON = ROOT / "venv/bin/python"
LOCK_ID = 741903126
SCENARIO_CODE = "AUTONOMOUS_EDGE_SEARCH"
EXECUTORS = {
    "SYNC_CONTRACT_SPECS": "src/scripts/sync_market_contract_specs_v1.py",
    "RESOLVE_FUTURES_ROLL": "src/scripts/build_futures_roll_decision_v1.py",
    "DISCOVER_REGIME": "src/scripts/build_edge_regime_hypothesis_discovery_v2.py",
    "WALKFORWARD": "src/scripts/build_walkforward_edge_search_v3.py",
    "METHODOLOGY_GATE": "src/scripts/evaluate_edge_methodology_contract_v1.py",
    "PROMOTE_OOS": "src/scripts/promote_regime_oos_to_canonical_v1.py",
    "VALIDATE_EDGE": "src/scripts/build_profit_funnel_validated_edge_v2.py",
    "OOS_FORWARD_HANDOFF": "src/scripts/build_profit_funnel_oos_forward_handoff_v2.py",
    "ADMIT_FORWARD": "src/scripts/admit_oos_forward_clean_cohort_v1.py",
    "OBSERVE_FORWARD": "src/scripts/run_forward_edge_observation_worker_v1.py",
    "PROJECT_SHADOW": "src/scripts/run_forward_pass_shadow_observer_v2.py",
    "ADMIT_PAPER": "src/scripts/build_profit_funnel_shadow_paper_admission_v2.py",
    "BUILD_LINEAGE": "src/scripts/build_profit_funnel_transition_lineage_v2.py",
    "ANALYZE_RESULTS": "src/scripts/analyze_edge_search_results_v1.py",
    "GENERATE_ADAPTIVE_SCENARIOS": "src/scripts/generate_adaptive_edge_search_scenarios_v1.py",
}


def load_scenario(connection):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT s.config_version,s.schedule_policy,s.result_policy,
                   jsonb_agg(jsonb_build_object(
                     'step_order',p.step_order,'executor_code',p.executor_code,
                     'timeout_seconds',p.timeout_seconds,'required',p.required
                   ) ORDER BY p.step_order)
            FROM analytics.edge_search_scenario_v1 s
            JOIN analytics.edge_search_scenario_step_v1 p USING (scenario_code)
            WHERE s.scenario_code=%s AND s.enabled AND p.enabled
            GROUP BY s.config_version,s.schedule_policy,s.result_policy
        """, (SCENARIO_CODE,))
        row = cursor.fetchone()
    if not row or not row[3]:
        raise RuntimeError("EDGE_SEARCH_SCENARIO_NOT_CONFIGURED")
    steps = row[3]
    unknown = [step["executor_code"] for step in steps if step["executor_code"] not in EXECUTORS]
    if unknown:
        raise RuntimeError("EDGE_SEARCH_EXECUTOR_NOT_ALLOWED:" + ",".join(unknown))
    return {"config_version": row[0], "schedule_policy": row[1], "result_policy": row[2], "steps": steps}


def persist_analysis(run_id, outcome, reason, markets, combinations, passes, *, technical_step=None):
    failed = outcome != "PASS_FOUND"
    technical_failure = outcome == "FAILED"
    explanation = (
        f"Технический сбой этапа {technical_step or 'UNKNOWN'}; торговый результат не оценивался. Система повторит сценарий после исправления."
        if technical_failure else
        "Найдено подтверждённое преимущество; допускается только дальнейшая стадия по политике PASS."
        if not failed else
        "Подтверждённое преимущество не найдено. Ограничения не ослабляются; причины сохранены для следующего системного цикла."
    )
    evidence = {"markets_evaluated": markets, "combinations_evaluated": combinations, "oos_pass": passes}
    with psycopg2.connect("postgresql:///finam_core") as connection:
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO analytics.edge_search_run_analysis_v1
                  (run_id,outcome_code,primary_reason_code,success_factors,failure_factors,
                   evidence,recommendation_code,explanation_ru)
                VALUES (%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s)
                ON CONFLICT (run_id) DO UPDATE SET
                  outcome_code=EXCLUDED.outcome_code,primary_reason_code=EXCLUDED.primary_reason_code,
                  success_factors=EXCLUDED.success_factors,failure_factors=EXCLUDED.failure_factors,
                  evidence=EXCLUDED.evidence,recommendation_code=EXCLUDED.recommendation_code,
                  explanation_ru=EXCLUDED.explanation_ru
            """, (str(run_id),outcome,reason,json.dumps(["OOS_PASS"] if passes else []),
                  json.dumps([reason] if failed else []),json.dumps(evidence),
                  "FIX_EXECUTOR_AND_RETRY_SYSTEM_SCHEDULE" if technical_failure else
                  ("PROMOTE_CONFIRMED_PASS" if passes else "KEEP_GATES_AND_EXPAND_EVIDENCE"),explanation))
            cursor.execute("""UPDATE marketcore_action.research_process_v1 p SET
                outcome_code=%s,reason_code=%s,
                recommendation_code=%s,explanation_ru=%s,updated_at=clock_timestamp()
                FROM analytics.edge_search_scenario_run_v1 r
                WHERE r.run_id=%s AND p.process_id=r.process_id""",
                (outcome,reason,
                 "FIX_EXECUTOR_AND_RETRY_SYSTEM_SCHEDULE" if technical_failure else
                 ("PROMOTE_CONFIRMED_PASS" if passes else "KEEP_GATES_AND_EXPAND_EVIDENCE"),
                 explanation,str(run_id)))


def session_freshness_minutes(now: datetime | None = None) -> int:
    current = now or datetime.now(ZoneInfo("Europe/Moscow"))
    if current.weekday() >= 5 or (current.weekday() == 0 and current.hour < 10):
        return 4320
    if current.hour < 10:
        return 720
    return 15


def resource_snapshot() -> dict[str, float]:
    load_1m = os.getloadavg()[0]
    available_kb = 0
    with open("/proc/meminfo", encoding="utf-8") as source:
        for line in source:
            if line.startswith("MemAvailable:"):
                available_kb = int(line.split()[1])
                break
    return {"load_1m": load_1m, "memory_available_mb": available_kb / 1024.0}


def heavy_search_window_open(now: datetime | None = None) -> bool:
    current = now or datetime.now(ZoneInfo("Europe/Moscow"))
    return current.weekday() >= 5 or current.hour < 9


def resource_block_reason(snapshot: dict[str, float], now: datetime | None = None) -> str | None:
    if os.getenv("EDGE_SEARCH_FORCE", "0") == "1":
        return None
    if not heavy_search_window_open(now):
        return "EDGE_SEARCH_OUTSIDE_LOW_LOAD_WINDOW"
    if snapshot["load_1m"] > float(os.getenv("EDGE_SEARCH_MAX_LOAD_1M", "2.5")):
        return "EDGE_SEARCH_SERVER_LOAD_HIGH"
    if snapshot["memory_available_mb"] < float(os.getenv("EDGE_SEARCH_MIN_MEMORY_MB", "3072")):
        return "EDGE_SEARCH_MEMORY_RESERVE_LOW"
    return None


def output_metric(output: str, name: str) -> int:
    matches = re.findall(rf"(?m)^{re.escape(name)}=(\d+)$", output)
    return int(matches[-1]) if matches else 0


def record_status(cycle_id: uuid.UUID, **values: object) -> None:
    assignments = ",".join(f"{key}=%s" for key in values)
    with psycopg2.connect("postgresql:///finam_core") as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE analytics.edge_search_cycle_status_v1 SET {assignments},updated_at=clock_timestamp() WHERE cycle_id=%s",
                (*values.values(), str(cycle_id)),
            )
            process_id = os.getenv("MARKETCORE_PROCESS_ID")
            if process_id:
                process_status = "FAILED" if values.get("status_code") == "FAILED" else "RUNNING"
                if values.get("finished_at") is not None and process_status != "FAILED":
                    process_status = "SUCCEEDED"
                progress = values.get("progress_pct")
                step = values.get("current_step")
                cursor.execute("""UPDATE marketcore_action.research_process_v1 SET
                    status_code=%s,progress_pct=coalesce(%s,progress_pct),
                    current_step_code=coalesce(%s,current_step_code),updated_at=clock_timestamp()
                    WHERE process_id=%s::uuid""",
                    (process_status,progress,step,process_id))
                cursor.execute("""INSERT INTO marketcore_action.research_process_event_v1
                    (process_id,event_code,status_code,progress_pct,step_code,payload)
                    SELECT process_id,'PROGRESS_UPDATED',status_code,progress_pct,current_step_code,%s::jsonb
                    FROM marketcore_action.research_process_v1 WHERE process_id=%s::uuid""",
                    (json.dumps(values,default=str),process_id))


def market_data_watermark(cursor, freshness_minutes: int):
    cursor.execute("""
        SELECT max(ts)
        FROM public.market_bars
        WHERE timeframe='M5'
          AND ts >= clock_timestamp()-(%s * interval '1 minute')
    """, (freshness_minutes,))
    return cursor.fetchone()[0]


def reconcile_stale_runs(connection) -> int:
    """The advisory lock is held, so any older RUNNING row has no live owner."""
    with connection.cursor() as cursor:
        cursor.execute("""
            WITH stale AS (
              UPDATE analytics.edge_search_scenario_run_v1
              SET status_code='FAILED',finished_at=clock_timestamp()
              WHERE status_code='RUNNING'
              RETURNING run_id,cycle_id
            ), failed_steps AS (
              UPDATE analytics.edge_search_step_run_v1 s
              SET status_code='FAILED',finished_at=clock_timestamp(),return_code=-2,
                  stderr_tail=concat_ws(E'\n',s.stderr_tail,'SYSTEM_PROCESS_TERMINATED_WITHOUT_FINAL_STATUS')
              FROM stale WHERE s.run_id=stale.run_id AND s.status_code='RUNNING'
              RETURNING s.run_id
            ), failed_cycles AS (
              UPDATE analytics.edge_search_cycle_status_v1 c
              SET status_code='FAILED',reason_code='EDGE_SEARCH_PROCESS_TERMINATED',
                  finished_at=clock_timestamp(),updated_at=clock_timestamp()
              FROM stale WHERE c.cycle_id=stale.cycle_id
              RETURNING c.cycle_id
            )
            INSERT INTO analytics.edge_search_run_analysis_v1
              (run_id,outcome_code,primary_reason_code,failure_factors,evidence,
               recommendation_code,explanation_ru)
            SELECT run_id,'FAILED','EDGE_SEARCH_PROCESS_TERMINATED',
                   '["TECHNICAL_PROCESS_TERMINATION"]'::jsonb,'{}'::jsonb,
                   'RETRY_ON_NEXT_SYSTEM_SCHEDULE',
                   'Процесс завершился без финального статуса; торговый результат не оценивался. Система закрыла зависшую запись.'
            FROM stale ON CONFLICT (run_id) DO NOTHING
            RETURNING run_id
        """)
        return len(cursor.fetchall())


def main() -> int:
    cycle_id = uuid.uuid4()
    run_id = uuid.uuid4()
    request_id = os.getenv("EDGE_SEARCH_REQUEST_ID")
    process_id = os.getenv("MARKETCORE_PROCESS_ID")
    freshness_minutes = int(os.getenv("EDGE_SEARCH_FRESHNESS_MINUTES", str(session_freshness_minutes())))
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": str(ROOT / "src"),
        "DATABASE_URL": "postgresql:///finam_core",
        "RUNTIME_ALLOW_TRADING": "0",
        "EXECUTION_ENABLED": "0",
        "REAL_TRADING_ENABLED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "EDGE_SEARCH_FRESHNESS_MINUTES": str(freshness_minutes),
        "EDGE_SEARCH_SCENARIO_RUN_ID": str(run_id),
    })
    with psycopg2.connect("postgresql:///finam_core") as lock_connection:
        with lock_connection.cursor() as cursor:
            if request_id:
                cursor.execute("""INSERT INTO marketcore_action.edge_search_request_run_v1(request_id,cycle_id,run_id)
                    VALUES(%s,%s,%s) ON CONFLICT(request_id) DO UPDATE SET cycle_id=EXCLUDED.cycle_id,
                    run_id=EXCLUDED.run_id,updated_at=clock_timestamp()""",
                    (request_id,str(cycle_id),str(run_id)))
            if process_id:
                cursor.execute("""UPDATE marketcore_action.research_process_v1 SET
                    cycle_id=%s,run_id=%s,status_code='RUNNING',progress_pct=5,
                    current_step_code='STARTING',updated_at=clock_timestamp()
                    WHERE process_id=%s::uuid""", (str(cycle_id),str(run_id),process_id))
                lock_connection.commit()
            cursor.execute("SELECT pg_try_advisory_lock(%s)", (LOCK_ID,))
            if not cursor.fetchone()[0]:
                print("cycle_skipped=1")
                print("reason=AUTONOMOUS_EDGE_SEARCH_ALREADY_RUNNING")
                print("live_allowed=0")
                print("VERDICT=AUTONOMOUS_EDGE_SEARCH_CYCLE_V1_OK")
                return 0
            stale_runs = reconcile_stale_runs(lock_connection)
            lock_connection.commit()  # Session advisory lock survives commit; audit repair becomes visible immediately.
            if stale_runs:
                print(f"stale_runs_reconciled={stale_runs}")
            snapshot = resource_snapshot()
            block_reason = resource_block_reason(snapshot)
            if block_reason:
                with psycopg2.connect("postgresql:///finam_core") as status_connection:
                    with status_connection.cursor() as status_cursor:
                        status_cursor.execute("""
                            INSERT INTO analytics.edge_search_cycle_status_v1 (
                                cycle_id,status_code,current_step,progress_pct,freshness_minutes,
                                reason_code,finished_at
                            ) VALUES (%s,'SKIPPED','RESOURCE_GUARD',100,%s,%s,clock_timestamp())
                        """, (str(cycle_id),freshness_minutes,block_reason))
                print(f"cycle_id={cycle_id}")
                print("cycle_status=SKIPPED")
                print(f"reason={block_reason}")
                print(f"load_1m={snapshot['load_1m']:.2f}")
                print(f"memory_available_mb={snapshot['memory_available_mb']:.0f}")
                print("live_allowed=0")
                print("VERDICT=AUTONOMOUS_EDGE_SEARCH_RESOURCE_GUARD_OK")
                return 0
            watermark = market_data_watermark(cursor, freshness_minutes)
            cursor.execute("""
                SELECT market_data_watermark
                FROM analytics.edge_search_cycle_status_v1
                WHERE status_code IN ('PASS_FOUND','NO_PASS','NO_CURRENT_MARKETS')
                  AND freshness_minutes=%s
                ORDER BY finished_at DESC NULLS LAST LIMIT 1
            """, (freshness_minutes,))
            previous = cursor.fetchone()
            previous_watermark = previous[0] if previous else None
            if (
                os.getenv("EDGE_SEARCH_FORCE", "0") != "1"
                and watermark is not None
                and watermark == previous_watermark
            ):
                with psycopg2.connect("postgresql:///finam_core") as status_connection:
                    with status_connection.cursor() as status_cursor:
                        status_cursor.execute("""
                            INSERT INTO analytics.edge_search_cycle_status_v1 (
                                cycle_id,status_code,current_step,progress_pct,freshness_minutes,
                                market_data_watermark,reason_code,finished_at
                            ) VALUES (%s,'SKIPPED','COMPLETE',100,%s,%s,
                                      'EDGE_SEARCH_DATA_UNCHANGED',clock_timestamp())
                        """, (str(cycle_id),freshness_minutes,watermark))
                print(f"cycle_id={cycle_id}")
                print("cycle_status=SKIPPED")
                print("reason=EDGE_SEARCH_DATA_UNCHANGED")
                print("live_allowed=0")
                print("VERDICT=AUTONOMOUS_EDGE_SEARCH_CYCLE_V1_OK")
                return 0
            # The advisory lock is session-scoped, so committing here keeps the
            # lock while releasing the snapshot transaction before long-running
            # executor subprocesses start.
            lock_connection.commit()
        with psycopg2.connect("postgresql:///finam_core") as status_connection:
            with status_connection.cursor() as status_cursor:
                status_cursor.execute("""
                    INSERT INTO analytics.edge_search_cycle_status_v1 (
                        cycle_id,status_code,current_step,progress_pct,freshness_minutes,
                        market_data_watermark,reason_code
                    ) VALUES (%s,'RUNNING','STARTING',0,%s,%s,'EDGE_SEARCH_STARTED')
                """, (str(cycle_id),freshness_minutes,watermark))
                scenario = load_scenario(status_connection)
                status_cursor.execute("""
                    INSERT INTO analytics.edge_search_scenario_run_v1
                      (run_id,cycle_id,scenario_code,status_code,config_snapshot,process_id)
                    VALUES (%s,%s,%s,'RUNNING',%s::jsonb,%s::uuid)
                """, (str(run_id),str(cycle_id),SCENARIO_CODE,json.dumps(scenario),process_id))
        markets_evaluated = combinations_evaluated = passes = 0
        steps = scenario["steps"]
        for step_index, step_config in enumerate(steps, start=1):
            executor_code = step_config["executor_code"]
            step = EXECUTORS[executor_code]
            step_run_id = uuid.uuid4()
            started = time.monotonic()
            with psycopg2.connect("postgresql:///finam_core") as connection:
                with connection.cursor() as cursor:
                    cursor.execute("""INSERT INTO analytics.edge_search_step_run_v1
                      (step_run_id,run_id,step_order,executor_code,status_code)
                      VALUES (%s,%s,%s,%s,'RUNNING')""",
                      (str(step_run_id),str(run_id),step_config["step_order"],executor_code))
            record_status(cycle_id,current_step=executor_code,progress_pct=int((step_index-1)*100/len(steps)))
            timed_out = False
            process = subprocess.Popen(
                (str(PYTHON), step), cwd=ROOT, env=env,
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            while True:
                try:
                    stdout, stderr = process.communicate(timeout=15)
                    result = subprocess.CompletedProcess(process.args,process.returncode,stdout,stderr)
                    break
                except subprocess.TimeoutExpired:
                    elapsed = time.monotonic() - started
                    if elapsed >= step_config["timeout_seconds"]:
                        timed_out = True
                        process.kill()
                        stdout, stderr = process.communicate()
                        stderr = f"{stderr}\nSTEP_TIMEOUT_SECONDS={step_config['timeout_seconds']}".strip()
                        result = subprocess.CompletedProcess(process.args,124,stdout,stderr)
                        break
                    record_status(cycle_id,current_step=executor_code)
                    if process_id:
                        with psycopg2.connect("postgresql:///finam_core") as heartbeat_connection:
                            with heartbeat_connection.cursor() as heartbeat_cursor:
                                heartbeat_cursor.execute(
                                    "UPDATE marketcore_action.research_process_v1 "
                                    "SET updated_at=clock_timestamp() WHERE process_id=%s::uuid AND status_code='RUNNING'",
                                    (process_id,),
                                )
            print(f"step={step}|returncode={result.returncode}")
            if result.stdout:
                print(result.stdout.rstrip())
                if step.endswith("build_edge_regime_hypothesis_discovery_v2.py"):
                    markets_evaluated = max(markets_evaluated,output_metric(result.stdout,"markets"))
                    combinations_evaluated += output_metric(result.stdout,"strategy_regime_pairs")
                    passes += output_metric(result.stdout,"oos_pass")
                elif step.endswith("build_walkforward_edge_search_v3.py"):
                    match = re.findall(r"(?m)^search_run_id=([0-9a-f-]{36})$", result.stdout)
                    if match:
                        env["EDGE_SEARCH_WALKFORWARD_RUN_ID"] = match[-1]
                    combinations_evaluated += output_metric(result.stdout,"candidates_evaluated")
                    passes += output_metric(result.stdout,"oos_pass")
                record_status(
                    cycle_id,markets_evaluated=markets_evaluated,
                    combinations_evaluated=combinations_evaluated,oos_pass=passes,
                    progress_pct=int(step_index*100/len(steps)),
                )
            metrics = {"markets": output_metric(result.stdout,"markets"),
                       "candidates_evaluated": output_metric(result.stdout,"candidates_evaluated"),
                       "oos_pass": output_metric(result.stdout,"oos_pass")}
            with psycopg2.connect("postgresql:///finam_core") as connection:
                with connection.cursor() as cursor:
                    cursor.execute("""UPDATE analytics.edge_search_step_run_v1 SET
                      status_code=%s,finished_at=clock_timestamp(),duration_ms=%s,return_code=%s,
                      metrics=%s::jsonb,stdout_tail=%s,stderr_tail=%s WHERE step_run_id=%s""",
                      ("SUCCEEDED" if result.returncode == 0 else "FAILED",int((time.monotonic()-started)*1000),
                       result.returncode,json.dumps(metrics),result.stdout[-8000:],result.stderr[-8000:],str(step_run_id)))
            if result.returncode != 0:
                if result.stderr:
                    print(result.stderr.rstrip())
                print("VERDICT=AUTONOMOUS_EDGE_SEARCH_CYCLE_FAILED")
                technical_reason = f"EDGE_SEARCH_STEP_TIMEOUT:{executor_code}" if timed_out else f"EDGE_SEARCH_EXECUTOR_FAILED:{executor_code}"
                record_status(
                    cycle_id,status_code="FAILED",reason_code=technical_reason,
                    finished_at=datetime.now(ZoneInfo("Europe/Moscow")),progress_pct=int(step_index*100/len(steps)),
                )
                with psycopg2.connect("postgresql:///finam_core") as connection:
                    with connection.cursor() as cursor:
                        cursor.execute("UPDATE analytics.edge_search_scenario_run_v1 SET status_code='FAILED',finished_at=clock_timestamp() WHERE run_id=%s",(str(run_id),))
                persist_analysis(
                    run_id,"FAILED",technical_reason,
                    markets_evaluated,combinations_evaluated,passes,technical_step=executor_code,
                )
                return 2
    outcome = "NO_CURRENT_MARKETS" if markets_evaluated == 0 else ("PASS_FOUND" if passes else "NO_PASS")
    reason = {
        "NO_CURRENT_MARKETS": "EDGE_SEARCH_NO_CURRENT_MARKETS",
        "PASS_FOUND": "EDGE_SEARCH_OOS_PASS_FOUND",
        "NO_PASS": "EDGE_SEARCH_COMPLETED_WITHOUT_PASS",
    }[outcome]
    record_status(
        cycle_id,status_code=outcome,current_step="COMPLETE",progress_pct=100,
        markets_evaluated=markets_evaluated,combinations_evaluated=combinations_evaluated,
        oos_pass=passes,reason_code=reason,finished_at=datetime.now(ZoneInfo("Europe/Moscow")),
    )
    with psycopg2.connect("postgresql:///finam_core") as connection:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE analytics.edge_search_scenario_run_v1 SET status_code='SUCCEEDED',finished_at=clock_timestamp() WHERE run_id=%s",(str(run_id),))
    persist_analysis(run_id,outcome,reason,markets_evaluated,combinations_evaluated,passes)
    print(f"cycle_id={cycle_id}")
    print(f"cycle_status={outcome}")
    print(f"freshness_minutes={freshness_minutes}")
    print(f"markets_evaluated={markets_evaluated}")
    print(f"combinations_evaluated={combinations_evaluated}")
    print(f"oos_pass={passes}")
    print("paper_promotion_changed=0")
    print("runtime_changed=0")
    print("live_allowed=0")
    print("VERDICT=AUTONOMOUS_EDGE_SEARCH_CYCLE_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
