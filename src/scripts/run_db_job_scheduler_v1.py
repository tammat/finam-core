from __future__ import annotations

import os
import subprocess
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
EXECUTORS = {
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
}


def due(row: dict, now: datetime, last_started: datetime | None) -> bool:
    local = now.astimezone(ZoneInfo(row["timezone_code"]))
    if local.weekday() not in row["weekdays"]:
        return False
    if not (row["window_start"] <= local.time().replace(tzinfo=None) <= row["window_end"]):
        return False
    return last_started is None or (now-last_started).total_seconds() >= row["interval_minutes"]*60


def main() -> int:
    launched = 0
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(%s) locked", (LOCK_ID,))
            if not cursor.fetchone()["locked"]:
                print("VERDICT=DB_JOB_SCHEDULER_ALREADY_RUNNING")
                return 0
            cursor.execute("SELECT * FROM analytics.system_job_schedule_v1 WHERE enabled ORDER BY priority,job_code")
            jobs = cursor.fetchall()
            for job in jobs:
                if job["executor_code"] not in EXECUTORS:
                    raise RuntimeError("SYSTEM_JOB_EXECUTOR_NOT_ALLOWED:"+job["executor_code"])
                cursor.execute("SELECT max(started_at) last_started FROM analytics.system_job_run_v1 WHERE job_code=%s AND status_code='COMPLETE'", (job["job_code"],))
                last_started = cursor.fetchone()["last_started"]
                now = datetime.now(ZoneInfo("UTC"))
                if not due(job, now, last_started):
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
                command = ["nice","-n","10","ionice","-c","2","-n","5",str(PYTHON),EXECUTORS[job["executor_code"]]]
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
                launched += 1
    print(f"jobs_launched={launched}")
    print("VERDICT=DB_JOB_SCHEDULER_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
