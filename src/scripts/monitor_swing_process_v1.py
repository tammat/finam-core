from __future__ import annotations
import os
from datetime import datetime,timedelta,timezone
import uuid
import psycopg2,psycopg2.extras

DB=os.getenv("DATABASE_URL","postgresql:///finam_core")
INTERVAL_HOURS={"H1":1,"H4":4,"D1":24}
STALE_HOURS={"H1":4,"H4":12,"D1":72}

def estimate_ready(latest,remaining,timeframe):
  if latest is None: return None
  if timeframe!="D1": return latest+timedelta(hours=remaining*INTERVAL_HOURS[timeframe])
  result=latest; added=0
  while added<remaining:
    result+=timedelta(days=1)
    if result.weekday()<5: added+=1
  return result

with psycopg2.connect(DB) as connection:
  with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
    cursor.execute("""UPDATE analytics.swing_next_research_plan_v1
      SET status_code='WAITING_FUTURE_DATA',last_error_code='STALE_HEARTBEAT_RECOVERED',updated_at=clock_timestamp()
      WHERE status_code='ACTIVE' AND heartbeat_at<clock_timestamp()-interval '30 minutes' RETURNING plan_id""")
    recovered=len(cursor.fetchall())
    cursor.execute("SELECT plan_id FROM analytics.swing_next_research_plan_v1 WHERE status_code IN ('WAITING_FUTURE_DATA','ACTIVE') ORDER BY created_at DESC LIMIT 1")
    plan=cursor.fetchone(); stale=ready=waiting=0
    monitor_run_id=uuid.uuid4()
    if plan:
      cursor.execute("SELECT * FROM analytics.swing_next_research_plan_item_v1 WHERE plan_id=%s AND status_code IN ('WAITING_FUTURE_DATA','ACTIVE') ORDER BY priority",(plan["plan_id"],))
      items=cursor.fetchall(); now=datetime.now(timezone.utc)
      for item in items:
        cursor.execute("""SELECT count(*) FILTER(WHERE ts>%s) accumulated,max(ts) latest
          FROM analytics.swing_market_bars_v1 WHERE symbol=%s AND timeframe=%s""",
          (item["confirmation_after_ts"],item["symbol"],item["timeframe"]))
        source=cursor.fetchone(); accumulated=int(source["accumulated"] or 0)
        required=int(item["minimum_future_bars"]); remaining=max(0,required-accumulated)
        latest=source["latest"]; age=(now-latest).total_seconds()/3600 if latest else None
        if accumulated>=required: status,reason="READY","FUTURE_SAMPLE_READY"; ready+=1
        elif latest is None: status,reason="NO_SOURCE","SWING_BAR_SOURCE_MISSING"; stale+=1
        elif age>STALE_HOURS[item["timeframe"]]: status,reason="STALE","SWING_BAR_SOURCE_STALE"; stale+=1
        else: status,reason="WAITING","ACCUMULATING_FUTURE_BARS"; waiting+=1
        eta=estimate_ready(latest,remaining,item["timeframe"])
        cursor.execute("""INSERT INTO analytics.swing_future_data_readiness_v1
          (monitor_run_id,plan_item_id,accumulated_bars,required_bars,remaining_bars,latest_bar_ts,
           source_age_hours,readiness_status,estimated_ready_at,reason_code)
          VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
          (monitor_run_id,item["plan_item_id"],accumulated,required,remaining,latest,age,status,eta,reason))
      if stale:
        cursor.execute("UPDATE analytics.swing_next_research_plan_v1 SET last_error_code='FUTURE_DATA_SOURCE_STALE',updated_at=clock_timestamp() WHERE plan_id=%s",(plan["plan_id"],))
      else:
        cursor.execute("UPDATE analytics.swing_next_research_plan_v1 SET last_error_code=NULL,updated_at=clock_timestamp() WHERE plan_id=%s AND last_error_code='FUTURE_DATA_SOURCE_STALE'",(plan["plan_id"],))

print(f"recovered={recovered}")
print(f"future_ready={ready}")
print(f"future_waiting={waiting}")
print(f"future_stale={stale}")
print("VERDICT=SWING_PROCESS_MONITOR_V1_OK")
