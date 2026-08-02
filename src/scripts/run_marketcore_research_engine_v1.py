from __future__ import annotations

import json,os,subprocess
from pathlib import Path
import psycopg2,psycopg2.extras

ROOT=Path(__file__).resolve().parents[2]
PYTHON=ROOT/"venv/bin/python"
DB=os.getenv("DATABASE_URL","postgresql:///finam_core")
STEPS=(
 "src/scripts/run_v5_purged_oos_worker_v1.py",
 "src/scripts/run_execution_spec_parity_replay_v1.py",
 "src/scripts/run_observation_parity_replay_v1.py",
 "src/scripts/run_swing_parity_replay_v1.py",
)

def engine_status(row):
 if row["spec_mismatch"] or row["observation_mismatch"] or row["swing_mismatch"]: return "BLOCKED"
 if row["v5_fail"] and not row["v5_collecting"]: return "FAIL"
 if row["v5_pass"] and row["spec_match"]>=row["v5_pass"]: return "PASS"
 if row["frozen_candidates"]: return "COLLECTING"
 return "IDLE"

def main():
 env=dict(os.environ,PYTHONPATH="src",PYTHONDONTWRITEBYTECODE="1",
          EXECUTION_ENABLED="0",REAL_TRADING_ENABLED="0",RUNTIME_ALLOW_TRADING="0")
 with psycopg2.connect(DB) as lock:
  lock.autocommit=True
  with lock.cursor() as q:
   q.execute("SELECT pg_try_advisory_lock(hashtext('marketcore_research_engine_v1'))")
   if not q.fetchone()[0]: print("VERDICT=MARKETCORE_RESEARCH_ENGINE_ALREADY_RUNNING");return 0
  try:
   for step in STEPS:
    result=subprocess.run([str(PYTHON),step],cwd=ROOT,env=env,text=True,capture_output=True,check=False)
    print(f"step={step} rc={result.returncode}")
    if result.stdout: print(result.stdout[-1000:].rstrip())
    if result.returncode:
     if result.stderr: print(result.stderr[-1000:].rstrip())
     print(f"VERDICT=MARKETCORE_RESEARCH_ENGINE_BLOCKED step={step}");return result.returncode
   with psycopg2.connect(DB) as conn,conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as q:
    q.execute("""SELECT
      (SELECT count(*) FROM analytics.v5_post_fix_branch_registry_v1) frozen_candidates,
      (SELECT count(*) FROM analytics.v5_oos_run_v1 v JOIN analytics.v5_post_fix_branch_registry_v1 r USING(admission_id) WHERE v.status_code='COLLECTING') v5_collecting,
      (SELECT count(*) FROM analytics.v5_oos_run_v1 v JOIN analytics.v5_post_fix_branch_registry_v1 r USING(admission_id) WHERE v.status_code='OOS_PASS') v5_pass,
      (SELECT count(*) FROM analytics.v5_oos_run_v1 v JOIN analytics.v5_post_fix_branch_registry_v1 r USING(admission_id) WHERE v.status_code='OOS_FAIL') v5_fail,
      (SELECT count(*) FROM analytics.execution_spec_parity_v1 WHERE verdict_code='MATCH') spec_match,
      (SELECT count(*) FROM analytics.execution_spec_parity_v1 WHERE verdict_code='MISMATCH') spec_mismatch,
      (SELECT count(*) FROM analytics.execution_spec_parity_v1 WHERE verdict_code='NOT_PROVEN') spec_not_proven,
      (SELECT count(*) FROM analytics.observation_parity_v1 WHERE verdict_code='MATCH') observation_match,
      (SELECT count(*) FROM analytics.observation_parity_v1 WHERE verdict_code='MISMATCH') observation_mismatch,
      (SELECT count(*) FROM analytics.observation_parity_v1 WHERE verdict_code='NOT_PROVEN') observation_not_proven,
      (SELECT count(*) FROM analytics.swing_candidate_lifecycle_v1) swing_candidates,
      (SELECT count(*) FROM analytics.swing_parity_v1 WHERE spec_verdict='MATCH') swing_match,
      (SELECT count(*) FROM analytics.swing_parity_v1 WHERE spec_verdict='MISMATCH') swing_mismatch,
      (SELECT count(*) FROM analytics.swing_parity_v1 WHERE spec_verdict='NOT_PROVEN') swing_not_proven,
      (SELECT count(*) FROM analytics.entry_exit_runtime_profile_v1 WHERE status='ACTIVE') active_paper_profiles""")
    row=dict(q.fetchone());status=engine_status(row)
    q.execute("""INSERT INTO analytics.marketcore_research_engine_snapshot_v1(
      engine_status,frozen_candidates,v5_collecting,v5_pass,v5_fail,spec_match,spec_mismatch,
      spec_not_proven,observation_match,observation_mismatch,observation_not_proven,
      swing_candidates,swing_match,swing_mismatch,swing_not_proven,active_paper_profiles,details)
      VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
      (status,*row.values(),psycopg2.extras.Json({"steps":STEPS,"trading_enabled":False})))
    print(json.dumps({"engine_status":status,**row},default=str,ensure_ascii=False))
   print("VERDICT=MARKETCORE_RESEARCH_ENGINE_V1_OK");return 0
  finally:
   with lock.cursor() as q:q.execute("SELECT pg_advisory_unlock(hashtext('marketcore_research_engine_v1'))")
if __name__=="__main__":raise SystemExit(main())
