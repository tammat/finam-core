import os,psycopg2
DB=os.getenv("DATABASE_URL","postgresql:///finam_core")
with psycopg2.connect(DB) as c:
  with c.cursor() as q:
    q.execute("""UPDATE analytics.swing_next_research_plan_v1 SET status_code='WAITING_FUTURE_DATA',last_error_code='STALE_HEARTBEAT_RECOVERED',updated_at=clock_timestamp()
      WHERE status_code='ACTIVE' AND heartbeat_at<clock_timestamp()-interval '30 minutes' RETURNING plan_id""")
    n=len(q.fetchall())
print(f"recovered={n}");print("VERDICT=SWING_PROCESS_MONITOR_V1_OK")
