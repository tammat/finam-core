from __future__ import annotations

import hashlib,json,os,uuid
from datetime import datetime,timezone
import psycopg2
import psycopg2.extras

DB=os.getenv("DATABASE_URL","postgresql:///finam_core")
NAMESPACE=uuid.UUID("c8a3fe1a-96e0-49bb-8d3e-bcf45fa8b11d")

def fp(code:str)->str:return hashlib.sha256(code.encode()).hexdigest()

def main()->int:
  conditions={}
  with psycopg2.connect(DB) as connection:
   with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
    cursor.execute("SELECT * FROM analytics.forward_pass_shadow_heartbeat_v1 WHERE worker_code='FORWARD_PASS_SHADOW_OBSERVER'")
    h=cursor.fetchone()
    now=datetime.now(timezone.utc)
    if not h or not h["last_success_at"]:
        conditions["SHADOW_HEARTBEAT_MISSING"]=("WARNING","SHADOW_OBSERVER_NEVER_SUCCEEDED",{})
    else:
        age=int((now-h["last_success_at"]).total_seconds())
        if age>600:conditions["SHADOW_HEARTBEAT_STALE"]=("CRITICAL","SHADOW_HEARTBEAT_OLDER_THAN_10_MINUTES",{"age_seconds":age})
    if h and h["status_code"]=="FAILED":
        conditions["SHADOW_OBSERVER_FAILED"]=("CRITICAL",h["last_error_code"] or "SHADOW_OBSERVER_FAILED",{"detail":h["last_error_detail"]})
    if h and h["unsafe_rows"]>0:
        conditions["SHADOW_UNSAFE_ROWS"]=("CRITICAL","SHADOW_EXECUTION_SAFETY_VIOLATION",{"unsafe_rows":h["unsafe_rows"]})
    cursor.execute("""SELECT status_code,job_code,started_at FROM analytics.system_job_run_v1
                       WHERE status_code IN ('FAILED','TIMEOUT') AND started_at>clock_timestamp()-interval '15 minutes'
                       ORDER BY started_at DESC LIMIT 1""")
    failed=cursor.fetchone()
    if failed:conditions["SHADOW_SCHEDULER_JOB_FAILED"]=("CRITICAL","SHADOW_SYSTEM_JOB_FAILED",dict(failed))
    known=("SHADOW_HEARTBEAT_MISSING","SHADOW_HEARTBEAT_STALE","SHADOW_OBSERVER_FAILED","SHADOW_UNSAFE_ROWS","SHADOW_SCHEDULER_JOB_FAILED")
    for code in known:
      fingerprint=fp(code)
      if code in conditions:
        severity,reason,evidence=conditions[code]
        alert_id=uuid.uuid5(NAMESPACE,code)
        cursor.execute("""INSERT INTO analytics.shadow_pipeline_alert_v1(
          alert_id,alert_code,severity_code,status_code,reason_code,evidence,alert_fingerprint)
          VALUES(%s,%s,%s,'OPEN',%s,%s,%s) ON CONFLICT(alert_fingerprint) DO UPDATE SET
          severity_code=EXCLUDED.severity_code,status_code='OPEN',reason_code=EXCLUDED.reason_code,
          evidence=EXCLUDED.evidence,resolved_at=NULL,updated_at=clock_timestamp()""",
          (str(alert_id),code,severity,reason,psycopg2.extras.Json(json.loads(json.dumps(evidence,default=str))),fingerprint))
      else:
        cursor.execute("""UPDATE analytics.shadow_pipeline_alert_v1 SET status_code='RESOLVED',
          resolved_at=clock_timestamp(),updated_at=clock_timestamp()
          WHERE alert_fingerprint=%s AND status_code='OPEN'""",(fingerprint,))
  print(f"open_alerts={len(conditions)}");print("VERDICT=SHADOW_PIPELINE_MONITOR_V1_OK");return 0

if __name__=="__main__":raise SystemExit(main())
