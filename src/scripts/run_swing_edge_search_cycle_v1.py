from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from pathlib import Path

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
ROOT = Path("/opt/finam-core")
PYTHON = ROOT / "venv/bin/python"
VERSION = "SWING_EDGE_SEARCH_V3_INDEPENDENT_TRADES"
NAMESPACE = uuid.UUID("64291888-3215-5a73-9abc-6110d5a38f6b")
LOCK_ID = 741903136
STEPS = (
    (1, "BUILD_TIMEFRAMES", "src/scripts/build_canonical_swing_timeframes_v1.py", 1800),
    (2, "DATA_QUALITY", "src/scripts/build_swing_data_quality_gate_v1.py", 300),
    (3, "GENERATE_HYPOTHESES", "src/scripts/build_swing_hypothesis_factory_v1.py", 900),
    (4, "SELECTION_VALIDATION", "src/scripts/run_swing_selection_validation_engine_v1.py", 1800),
)


def main() -> int:
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(%s) locked", (LOCK_ID,))
            if not cursor.fetchone()["locked"]:
                print("VERDICT=SWING_EDGE_SEARCH_ALREADY_RUNNING")
                return 0
            cursor.execute("""SELECT plan_id,reason_summary FROM analytics.edge_next_research_plan_v1
                WHERE status_code IN ('WAITING_FUTURE_DATA','ACTIVE','EVALUATED')
                ORDER BY created_at DESC LIMIT 1""")
            plan = cursor.fetchone()
            if not plan:
                print("reason=SWING_SOURCE_FAILURE_PLAN_MISSING")
                print("VERDICT=SWING_EDGE_SEARCH_WAITING_FOR_FAIL_PLAN")
                return 0
            run_id = uuid.uuid5(NAMESPACE, f"{plan['plan_id']}:{VERSION}")
            cursor.execute("SELECT status_code FROM analytics.swing_edge_search_run_v1 WHERE run_id=%s", (str(run_id),))
            prior = cursor.fetchone()
            if prior and prior["status_code"] in ("SUCCEEDED", "NO_PASS"):
                print(f"run_id={run_id}")
                print("VERDICT=SWING_EDGE_SEARCH_PLAN_ALREADY_EVALUATED")
                return 0
            cursor.execute("""INSERT INTO analytics.swing_edge_search_run_v1
                (run_id,scenario_code,source_plan_id,source_failure_reasons,status_code,current_step,progress_pct,config_version)
                VALUES(%s,'SWING_EDGE_SEARCH',%s,%s,'RUNNING','STARTING',0,%s)
                ON CONFLICT(run_id) DO UPDATE SET status_code='RUNNING',current_step='STARTING',
                  progress_pct=0,started_at=clock_timestamp(),finished_at=NULL,reason_code=NULL""",
                (str(run_id),str(plan["plan_id"]),psycopg2.extras.Json(sorted((plan["reason_summary"] or {}).keys())),VERSION))
            connection.commit()

            env = os.environ.copy()
            env.update({"PYTHONPATH": str(ROOT / "src"), "DATABASE_URL": DB,
                        "SWING_SOURCE_PLAN_ID": str(plan["plan_id"]),
                        "RUNTIME_ALLOW_TRADING": "0", "EXECUTION_ENABLED": "0",
                        "REAL_TRADING_ENABLED": "0", "PYTHONDONTWRITEBYTECODE": "1"})
            validation_pass = 0
            for order, code, script, timeout in STEPS:
                step_run_id = uuid.uuid5(NAMESPACE, f"{run_id}:{order}:{code}")
                cursor.execute("""INSERT INTO analytics.swing_edge_search_step_run_v1
                    (step_run_id,run_id,step_order,step_code,status_code)
                    VALUES(%s,%s,%s,%s,'RUNNING') ON CONFLICT(step_run_id) DO UPDATE SET
                    status_code='RUNNING',started_at=clock_timestamp(),finished_at=NULL,stderr_tail=NULL""",
                    (str(step_run_id),str(run_id),order,code))
                cursor.execute("""UPDATE analytics.swing_edge_search_run_v1 SET current_step=%s,
                    progress_pct=%s,updated_at=clock_timestamp() WHERE run_id=%s""",
                    (code,int((order-1)*100/len(STEPS)),str(run_id)))
                connection.commit()
                started = time.monotonic()
                result = subprocess.run((str(PYTHON),script),cwd=ROOT,env=env,text=True,
                                        capture_output=True,timeout=timeout,check=False)
                for line in result.stdout.splitlines():
                    if line.startswith("validation_pass="):
                        validation_pass = int(line.split("=",1)[1])
                cursor.execute("""UPDATE analytics.swing_edge_search_step_run_v1 SET status_code=%s,
                    finished_at=clock_timestamp(),duration_ms=%s,return_code=%s,stdout_tail=%s,stderr_tail=%s
                    WHERE step_run_id=%s""", ("SUCCEEDED" if result.returncode == 0 else "FAILED",
                    int((time.monotonic()-started)*1000),result.returncode,result.stdout[-8000:],result.stderr[-8000:],str(step_run_id)))
                if result.returncode != 0:
                    cursor.execute("""UPDATE analytics.swing_edge_search_run_v1 SET status_code='FAILED',
                        current_step=%s,reason_code=%s,finished_at=clock_timestamp(),updated_at=clock_timestamp()
                        WHERE run_id=%s""",(code,f"SWING_STEP_FAILED:{code}",str(run_id)))
                    connection.commit()
                    print(result.stderr)
                    print("VERDICT=SWING_EDGE_SEARCH_FAILED")
                    return 2
                connection.commit()
            status = "SUCCEEDED" if validation_pass else "NO_PASS"
            reason = "SWING_VALIDATION_PASS_FOUND" if validation_pass else "SWING_VALIDATION_COMPLETED_WITHOUT_PASS"
            cursor.execute("""UPDATE analytics.swing_edge_search_run_v1 SET status_code=%s,current_step='COMPLETE',
                progress_pct=100,validation_pass=%s,reason_code=%s,finished_at=clock_timestamp(),updated_at=clock_timestamp()
                WHERE run_id=%s""",(status,validation_pass,reason,str(run_id)))
            connection.commit()
    print(f"run_id={run_id}")
    print(f"validation_pass={validation_pass}")
    print("pass_gates=UNCHANGED")
    print("live_allowed=0")
    print("VERDICT=SWING_EDGE_SEARCH_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
