from __future__ import annotations
import os
import psycopg2

DB=os.getenv("DATABASE_URL","postgresql:///finam_core")

def main():
    with psycopg2.connect(DB) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(941903132)")
            if not cursor.fetchone()[0]:
                print("VERDICT=RESEARCH_PROCESS_MONITOR_ALREADY_RUNNING"); return 0
            cursor.execute("""WITH stale AS (
              UPDATE marketcore_action.command_request_v2 SET status='FAILED',finished_at=clock_timestamp(),
                failure_code=CASE status WHEN 'PENDING' THEN 'REQUEST_STALLED_PENDING' ELSE 'REQUEST_STALLED_RUNNING' END
              WHERE (status='PENDING' AND requested_at<clock_timestamp()-interval '60 minutes')
                 OR (status='RUNNING' AND started_at<clock_timestamp()-interval '90 minutes')
              RETURNING request_id,process_id,failure_code)
              INSERT INTO analytics.research_process_monitor_event_v1(request_id,process_id,event_code,detail)
              SELECT request_id,process_id,'STALE_REQUEST_FAILED',failure_code FROM stale
              ON CONFLICT DO NOTHING""")
            command_events=cursor.rowcount
            cursor.execute("""WITH stale AS (
              UPDATE marketcore_action.research_process_v1 p SET status_code='SKIPPED',progress_pct=100,
                current_step_code='ORPHAN_QUEUE_CLOSED',outcome_code='SKIPPED',
                reason_code='ORPHAN_PENDING_WITHOUT_REQUEST',
                explanation_ru='Старая заявка свёрнута: активная команда для неё отсутствует.',
                finished_at=clock_timestamp(),updated_at=clock_timestamp()
              WHERE p.status_code='PENDING'
                AND p.requested_at<clock_timestamp()-interval '60 minutes'
                AND NOT EXISTS(SELECT 1 FROM marketcore_action.command_request_v2 q
                  WHERE q.process_id=p.process_id AND q.status IN('PENDING','RUNNING'))
              RETURNING p.process_id)
              INSERT INTO analytics.research_process_monitor_event_v1(process_id,event_code,detail)
              SELECT process_id,'ORPHAN_PENDING_SKIPPED','ORPHAN_PENDING_WITHOUT_REQUEST' FROM stale
              ON CONFLICT DO NOTHING""")
            orphan_events=cursor.rowcount
            cursor.execute("""WITH stale AS (
              UPDATE marketcore_action.research_process_v1 p SET status_code='FAILED',progress_pct=100,
                current_step_code='MONITOR_TIMEOUT',outcome_code='FAILED',reason_code='PROCESS_HEARTBEAT_STALE',
                explanation_ru='Процесс остановлен монитором: обновление состояния не поступило вовремя.',
                finished_at=clock_timestamp(),updated_at=clock_timestamp()
              WHERE p.status_code='RUNNING' AND p.updated_at<clock_timestamp()-interval '90 minutes'
                AND NOT EXISTS(SELECT 1 FROM marketcore_action.command_request_v2 q
                  WHERE q.process_id=p.process_id AND q.status IN('PENDING','RUNNING'))
              RETURNING p.process_id)
              INSERT INTO analytics.research_process_monitor_event_v1(process_id,event_code,detail)
              SELECT process_id,'STALE_PROCESS_FAILED','PROCESS_HEARTBEAT_STALE' FROM stale
              ON CONFLICT DO NOTHING""")
            process_events=cursor.rowcount
    print(f"command_events={command_events} orphan_events={orphan_events} process_events={process_events}")
    print("VERDICT=RESEARCH_PROCESS_MONITOR_V1_OK"); return 0

if __name__=="__main__": raise SystemExit(main())
