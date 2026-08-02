from __future__ import annotations

import os
import subprocess
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
ROOT = Path("/opt/finam-core")
PYTHON = ROOT / "venv/bin/python"
LOCK_ID = 941903128
DEFAULT_HEAVY_LOAD_LIMIT = 3.0
EXECUTORS = {
    "RESEARCH_PROCESS_MONITOR_V1": "src/scripts/monitor_research_processes_v1.py",
    "INSTRUMENT_SCOUT_V1": "src/scripts/run_autonomous_instrument_scout_v1.py",
    "CONTRACT_SPEC_SYNC_V1": "src/scripts/sync_market_contract_specs_v1.py",
    "SWING_EDGE_SEARCH_CYCLE_V1": "src/scripts/run_swing_edge_search_cycle_v1.py",
    "SWING_CLOSED_BAR_SEARCH_V1": "src/scripts/run_swing_closed_bar_search_v1.py",
    "SWING_BARS_REFRESH_V1": "src/scripts/build_canonical_swing_timeframes_v1.py",
    "SWING_NEXT_RESEARCH_PLAN_V1": "src/scripts/generate_next_swing_research_plan_v1.py",
    "SWING_FUTURE_EXECUTION_V1": "src/scripts/run_swing_future_execution_v1.py",
    "SWING_PROCESS_MONITOR_V1": "src/scripts/monitor_swing_process_v1.py",
    "SWING_AUTONOMOUS_LIFECYCLE_V1": "src/scripts/run_swing_autonomous_lifecycle_v1.py",
    "SWING_SHADOW_OBSERVER_V1": "src/scripts/run_swing_forward_shadow_router_v1.py",
    "SWING_PAPER_ENGINE_V1": "src/scripts/run_swing_paper_engine_v1.py",
    "SWING_PARITY_REPLAY_V1": "src/scripts/run_swing_parity_replay_v1.py",
    "EDGE_SEARCH_AUTO_ENQUEUE_V1": "src/scripts/enqueue_scheduled_edge_search_v1.py",
    "EDGE_SEARCH_QUEUE_MONITOR_V1": "src/scripts/monitor_edge_search_command_queue_v1.py",
    "EDGE_SEARCH_COMMAND_QUEUE_V1": "src/scripts/run_edge_search_command_queue_v1.py",
    "FORWARD_COHORT_RECONCILIATION_V1": "src/scripts/reconcile_forward_cohort_v1.py",
    "FORWARD_EVIDENCE_PIPELINE_V1": "src/scripts/run_forward_evidence_pipeline_v1.py",
    "FORWARD_PASS_PROGRESS_V1": "src/scripts/build_forward_pass_progress_v1.py",
    "FORWARD_REMEDIATION_SCENARIOS_V1": "src/scripts/generate_forward_remediation_scenarios_v1.py",
    "FORWARD_PASS_SHADOW_OBSERVER_V2": "src/scripts/run_forward_pass_shadow_observer_v2.py",
    "SHADOW_PIPELINE_MONITOR_V1": "src/scripts/monitor_shadow_pipeline_v1.py",
    "SHADOW_PASS_EVALUATOR_V1": "src/scripts/evaluate_shadow_pass_v1.py",
    "RESEARCH_QUEUE_GOVERNOR_V2": "src/scripts/govern_research_queues_v2.py",
    "SIGNAL_INTAKE_QUEUE_V2": "src/scripts/process_signal_intake_queue_v2.py",
    "EDGE_STRICT_RULE_BUILD_V2": "src/scripts/build_edge_strict_rules_v2.py",
    "PAPER_CLOSED_TRADE_MATERIALIZER_V2": "src/scripts/analytics/materialize_closed_trades_from_fills_v1.py",
    "PAPER_FILL_ANOMALY_DETECTOR_V1": "src/scripts/detect_paper_fill_anomalies_v1.py",
    "MARKET_OPEN_READINESS_V1": "src/scripts/check_market_open_readiness_v1.py",
    "HISTORICAL_EDGE_AUDIT_ENQUEUE_V1": "src/scripts/enqueue_historical_edge_audit_v1.py",
    "SIGNAL_FUNNEL_ANALYTICS_V1": "src/scripts/signal_funnel_analytics_v1.py",
    "SIGNAL_FUNNEL_REASON_ANALYTICS_V1": "src/scripts/signal_funnel_reason_analytics_v1.py",
    "MODEL_HEALTH_ENGINE_V1": "src/scripts/marketcore_model_health_engine_v1.py",
    "CHECKPOINTED_WALKFORWARD_V4": "src/scripts/run_checkpointed_walkforward_v4.py",
    "SESSION_EXECUTION_EDGE_V2": "src/scripts/build_session_execution_edge_v1.py",
    "OOS_REMEDIATION_BRANCH_GENERATOR_V1": "src/scripts/generate_oos_remediation_branches_v1.py",
    "MICROSTRUCTURE_PRIORITY_REFRESH_V1": "src/scripts/refresh_microstructure_priority_v1.py",
    "M15_REBUILD_FROM_M5_V1": "src/scripts/rebuild_m15_from_m5_v1.py",
    "HIERARCHICAL_EVIDENCE_ROUTER_V1": "src/scripts/build_v5_hierarchical_evidence_v1.py",
    "V5_ASSET_BRANCH_ROTATION_V1": "src/scripts/rotate_v5_asset_branch_timeframes_v1.py",
    "V5_FUTURES_FLAT_LIQUIDITY_ROLLOVER_V1": "src/scripts/run_v5_futures_rollover_v1.py",
    "V5_PURGED_OOS_WORKER_V1": "src/scripts/run_v5_purged_oos_worker_v1.py",
    "TRADE_OUTCOME_OOS_ADMISSION_V1": "src/scripts/admit_trade_outcome_hypotheses_to_oos_v1.py",
    "MX_INDEX_SHADOW_OBSERVER_V1": "src/scripts/build_mx_index_shadow_observer_v1.py",
    "RVI_REGIME_FEATURE_V1": "src/scripts/build_rvi_regime_feature_v1.py",
    "MARKET_REGIME_CONTEXT_V2": "src/scripts/build_market_regime_context_v2.py",
    "MONDAY_READINESS_V1": "src/scripts/analytics/build_monday_readiness_v1.py",
    "ADAPTIVE_PENDING_ENTRY_V1": "src/scripts/run_adaptive_pending_entry_worker_v1.py",
    "EXECUTION_SPEC_PARITY_REPLAY_V1": "src/scripts/run_execution_spec_parity_replay_v1.py",
    "OBSERVATION_PARITY_REPLAY_V1": "src/scripts/run_observation_parity_replay_v1.py",
    "LIGHTWEIGHT_STATISTICAL_EVIDENCE_V1": "src/scripts/analytics/build_lightweight_statistical_evidence_v1.py",
}

# These jobs scan history, rebuild bars, or evaluate many candidate paths.  On
# the four-core production host they may run only when enough CPU headroom is
# available.  The scheduler itself is serialized by LOCK_ID, therefore this
# also guarantees at most one scheduler-owned heavy job at a time.
HEAVY_EXECUTORS = {
    "INSTRUMENT_SCOUT_V1",
    "SWING_EDGE_SEARCH_CYCLE_V1",
    "SWING_CLOSED_BAR_SEARCH_V1",
    "SWING_BARS_REFRESH_V1",
    "SWING_AUTONOMOUS_LIFECYCLE_V1",
    "EDGE_SEARCH_COMMAND_QUEUE_V1",
    "HISTORICAL_EDGE_AUDIT_ENQUEUE_V1",
    "CHECKPOINTED_WALKFORWARD_V4",
    "SESSION_EXECUTION_EDGE_V2",
    "M15_REBUILD_FROM_M5_V1",
    "V5_PURGED_OOS_WORKER_V1",
    "LIGHTWEIGHT_STATISTICAL_EVIDENCE_V1",
}


def load_average_1m() -> float:
    try:
        return float(os.getloadavg()[0])
    except (AttributeError, OSError):
        return 0.0


def heavy_load_limit() -> float:
    try:
        return max(1.0, float(os.getenv("RESEARCH_HEAVY_LOAD_LIMIT", DEFAULT_HEAVY_LOAD_LIMIT)))
    except ValueError:
        return DEFAULT_HEAVY_LOAD_LIMIT


def resource_gate(executor_code: str) -> tuple[bool, float, float, str]:
    """Fail closed only for batch research; online Paper/readiness stays live."""
    load_1m = load_average_1m()
    limit = heavy_load_limit()
    if executor_code not in HEAVY_EXECUTORS:
        return True, load_1m, limit, "ONLINE_OR_LIGHT_JOB"
    if load_1m >= limit:
        return False, load_1m, limit, "HOST_LOAD_ABOVE_LIMIT"
    return True, load_1m, limit, "HEAVY_JOB_HEADROOM_AVAILABLE"


def audit_resource_gate(cursor, *, job_code: str, executor_code: str,
                        allowed: bool, load_1m: float, limit: float,
                        reason: str) -> None:
    cursor.execute("""INSERT INTO analytics.research_resource_gate_audit_v1(
        job_code,executor_code,decision_code,reason_code,load_1m,load_limit)
        VALUES(%s,%s,%s,%s,%s,%s)""", (
            job_code, executor_code, "ALLOW" if allowed else "DEFER",
            reason, load_1m, limit,
        ))


def research_cpu_limit(now: datetime) -> int:
    """Один CPU во время торгов, не более двух вне рынка."""
    local = now.astimezone(ZoneInfo("Europe/Moscow"))
    minute = local.hour * 60 + local.minute
    market_open = (
        (local.weekday() < 5 and 7 * 60 <= minute < 23 * 60 + 50)
        or (local.weekday() == 6 and 10 * 60 <= minute < 19 * 60)
    )
    return 1 if market_open else 2

EXECUTOR_ARGUMENTS = {
    "PAPER_CLOSED_TRADE_MATERIALIZER_V2": ["--apply"],
    "V5_FUTURES_FLAT_LIQUIDITY_ROLLOVER_V1": ["--apply"],
}

# Закрытия Paper влияют на свежий риск и expectancy, поэтому не получают
# фоновый nice=10. Остальные исследования остаются ограниченными.
EXECUTOR_NICE = {"PAPER_CLOSED_TRADE_MATERIALIZER_V2": 0}
EXECUTOR_IONICE = {"PAPER_CLOSED_TRADE_MATERIALIZER_V2": 3}
EXECUTOR_ENV = {
    # Сам планировщик остаётся на ограниченной peer-роли alex. Только
    # идемпотентный материализатор получает прикладную DB-роль для checkpoint.
    "PAPER_CLOSED_TRADE_MATERIALIZER_V2": {
        "DATABASE_URL": os.getenv("FINAM_DATABASE_URL", DB),
    },
    # Короткие возобновляемые пакеты не монополизируют четырёхъядерный сервер.
    "CHECKPOINTED_WALKFORWARD_V4": {"WALKFORWARD_BATCH_SECONDS": "45"},
    "SESSION_EXECUTION_EDGE_V2": {
        "SESSION_EDGE_MAX_MARKETS": "4",
        "SESSION_EDGE_MIN_BARS": "6000",
        "MICROSTRUCTURE_MIN_COVERAGE": "0.80",
        "MICROSTRUCTURE_MAX_QUOTE_DISTANCE_SECONDS": "5",
    },
    "LIGHTWEIGHT_STATISTICAL_EVIDENCE_V1": {
        "STAT_BOOTSTRAP_SAMPLES": "1000",
        "STAT_MAX_GROUPS": "100",
        "STAT_MAX_TRADES_PER_GROUP": "500",
    },
}


def due(row: dict, now: datetime, last_started: datetime | None) -> bool:
    local = now.astimezone(ZoneInfo(row["timezone_code"]))
    if local.weekday() not in row["weekdays"]:
        return False
    if not (row["window_start"] <= local.time().replace(tzinfo=None) <= row["window_end"]):
        return False
    return last_started is None or (now-last_started).total_seconds() >= row["interval_minutes"]*60


def reconcile_stale_running_jobs(cursor) -> list[dict]:
    """The scheduler lock proves no live scheduler owns an old RUNNING row."""
    cursor.execute("""
        UPDATE analytics.system_job_run_v1 run
        SET status_code='TIMEOUT',return_code=-2,finished_at=clock_timestamp(),
            stderr_tail=concat_ws(E'\n',nullif(run.stderr_tail,''),
              'SCHEDULER_RESTART_STALE_RUNNING_RECONCILED')
        FROM analytics.system_job_schedule_v1 schedule
        WHERE run.job_code=schedule.job_code
          AND run.status_code='RUNNING'
          AND run.started_at < clock_timestamp()
              - ((schedule.timeout_seconds + 60) * interval '1 second')
        RETURNING run.job_code,run.executor_code,run.scheduler_run_id,run.stderr_tail
    """)
    return [dict(row) for row in cursor.fetchall()]


def main() -> int:
    launched = 0
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(%s) locked", (LOCK_ID,))
            if not cursor.fetchone()["locked"]:
                print("VERDICT=DB_JOB_SCHEDULER_ALREADY_RUNNING")
                return 0
            stale_runs = reconcile_stale_running_jobs(cursor)
            connection.commit()
            if stale_runs:
                print(f"DB_JOB_STALE_RUNNING_RECONCILED count={len(stale_runs)}")
            cursor.execute("SELECT * FROM analytics.system_job_schedule_v1 WHERE enabled ORDER BY priority,job_code")
            jobs = cursor.fetchall()
            for job in jobs:
                if job["executor_code"] not in EXECUTORS:
                    # A stale or partially deployed research job must not stop
                    # every other allowlisted job in the shared scheduler.  Keep
                    # the fail-closed allowlist, persist the configuration error,
                    # and continue with the remaining independent jobs.
                    scheduler_run_id = uuid.uuid4()
                    failure = "SYSTEM_JOB_EXECUTOR_NOT_ALLOWED:" + job["executor_code"]
                    cursor.execute("""INSERT INTO analytics.system_job_run_v1(
                        scheduler_run_id,job_code,executor_code,status_code,
                        return_code,stderr_tail,finished_at)
                        VALUES(%s,%s,%s,'FAILED',126,%s,clock_timestamp())""",
                        (str(scheduler_run_id),job["job_code"],job["executor_code"],failure))
                    cursor.execute("""INSERT INTO analytics.system_job_failure_rollup_v1(
                        job_code,error_fingerprint,occurrences,first_seen_at,last_seen_at,
                        return_code,stdout_sample,stderr_sample)
                        VALUES(%s,md5(%s),1,clock_timestamp(),clock_timestamp(),126,'',%s)
                        ON CONFLICT(job_code,error_fingerprint) DO UPDATE SET
                          occurrences=analytics.system_job_failure_rollup_v1.occurrences+1,
                          last_seen_at=clock_timestamp(),return_code=excluded.return_code,
                          stderr_sample=excluded.stderr_sample,resolved_at=NULL""",
                        (job["job_code"],failure,failure))
                    connection.commit()
                    launched += 1
                    print(f"DB_JOB_SKIPPED job_code={job['job_code']} reason={failure}")
                    continue
                cursor.execute("SELECT max(started_at) last_started FROM analytics.system_job_run_v1 WHERE job_code=%s AND status_code='COMPLETE'", (job["job_code"],))
                last_started = cursor.fetchone()["last_started"]
                now = datetime.now(ZoneInfo("UTC"))
                if not due(job, now, last_started):
                    continue
                executor_code = job["executor_code"]
                allowed, load_1m, load_limit, gate_reason = resource_gate(executor_code)
                audit_resource_gate(
                    cursor, job_code=job["job_code"], executor_code=executor_code,
                    allowed=allowed, load_1m=load_1m, limit=load_limit,
                    reason=gate_reason,
                )
                connection.commit()
                if not allowed:
                    print(
                        f"DB_JOB_DEFERRED job_code={job['job_code']} "
                        f"load_1m={load_1m:.2f} limit={load_limit:.2f} "
                        f"reason={gate_reason}"
                    )
                    continue
                scheduler_run_id = uuid.uuid4()
                cursor.execute("""INSERT INTO analytics.system_job_run_v1(
                    scheduler_run_id,job_code,executor_code,status_code)
                    VALUES(%s,%s,%s,'RUNNING')""", (str(scheduler_run_id),job["job_code"],job["executor_code"]))
                connection.commit()
                env = os.environ.copy()
                env.update({"PYTHONPATH":str(ROOT/"src"),"DATABASE_URL":DB,
                            "RUNTIME_ALLOW_TRADING":"0","EXECUTION_ENABLED":"0","REAL_TRADING_ENABLED":"0",
                            "PYTHONDONTWRITEBYTECODE":"1"})
                env.update(EXECUTOR_ENV.get(executor_code, {}))
                cpu_limit = research_cpu_limit(now)
                env.update({
                    "OMP_NUM_THREADS": str(cpu_limit),
                    "OPENBLAS_NUM_THREADS": str(cpu_limit),
                    "MKL_NUM_THREADS": str(cpu_limit),
                    "NUMEXPR_NUM_THREADS": str(cpu_limit),
                    "PGOPTIONS": f"-c max_parallel_workers_per_gather={max(0,cpu_limit-1)}",
                })
                command = [
                    "nice", "-n", str(EXECUTOR_NICE.get(executor_code, 10)),
                    "ionice", "-c", "2", "-n", str(EXECUTOR_IONICE.get(executor_code, 5)),
                    str(PYTHON), EXECUTORS[executor_code],
                    *EXECUTOR_ARGUMENTS.get(executor_code, []),
                ]
                if shutil.which("taskset"):
                    command = ["taskset","--cpu-list","0" if cpu_limit == 1 else "0,1",*command]
                try:
                    result = subprocess.run(command,cwd=ROOT,env=env,text=True,capture_output=True,
                                            timeout=job["timeout_seconds"],check=False)
                    status = "COMPLETE" if result.returncode == 0 else "FAILED"
                    return_code = result.returncode
                    stdout,stderr = result.stdout[-4000:],result.stderr[-4000:]
                except subprocess.TimeoutExpired as error:
                    status,return_code = "TIMEOUT",-1
                    stdout=(error.stdout or "")[-4000:] if isinstance(error.stdout,str) else ""
                    stderr=(error.stderr or "")[-4000:] if isinstance(error.stderr,str) else ""
                cursor.execute("""UPDATE analytics.system_job_run_v1 SET status_code=%s,
                    return_code=%s,stdout_tail=%s,stderr_tail=%s,finished_at=clock_timestamp()
                    WHERE scheduler_run_id=%s""",(status,return_code,stdout,stderr,str(scheduler_run_id)))
                connection.commit()
                if status in {"FAILED", "TIMEOUT"}:
                    cursor.execute("""INSERT INTO analytics.system_job_failure_rollup_v1(
                        job_code,error_fingerprint,occurrences,first_seen_at,last_seen_at,return_code,stdout_sample,stderr_sample)
                      VALUES(%s,md5(%s||E'\\n'||%s),1,clock_timestamp(),clock_timestamp(),%s,%s,%s)
                      ON CONFLICT(job_code,error_fingerprint) DO UPDATE SET
                        occurrences=analytics.system_job_failure_rollup_v1.occurrences+1,
                        last_seen_at=clock_timestamp(),return_code=excluded.return_code,
                        stdout_sample=excluded.stdout_sample,stderr_sample=excluded.stderr_sample,resolved_at=NULL""",
                      (job["job_code"],stderr,stdout,return_code,stdout,stderr))
                    cursor.execute("""DELETE FROM analytics.system_job_run_v1
                      WHERE job_code=%s AND status_code IN('FAILED','TIMEOUT') AND scheduler_run_id<>%s
                        AND md5(coalesce(stderr_tail,'')||E'\\n'||coalesce(stdout_tail,''))=md5(%s||E'\\n'||%s)""",
                      (job["job_code"],str(scheduler_run_id),stderr,stdout))
                    connection.commit()
                elif status == "COMPLETE":
                    cursor.execute("""UPDATE analytics.system_job_failure_rollup_v1 SET resolved_at=coalesce(resolved_at,clock_timestamp())
                      WHERE job_code=%s AND resolved_at IS NULL""",(job["job_code"],))
                    connection.commit()
                launched += 1
    print(f"jobs_launched={launched}")
    print("VERDICT=DB_JOB_SCHEDULER_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
