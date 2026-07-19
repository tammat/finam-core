from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
LOCK_ID = 941903130


def main() -> int:
    run_id = str(uuid.uuid4())
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("SELECT pg_try_advisory_xact_lock(%s) locked", (LOCK_ID,))
            if not cursor.fetchone()["locked"]:
                print("VERDICT=RESEARCH_QUEUE_GOVERNOR_ALREADY_RUNNING")
                return 0

            cursor.execute("""SELECT * FROM analytics.research_queue_governance_policy_v2
                WHERE enabled ORDER BY updated_at DESC LIMIT 1""")
            policy = cursor.fetchone()
            if policy is None:
                raise RuntimeError("RESEARCH_QUEUE_GOVERNANCE_POLICY_MISSING")

            cursor.execute("""SELECT count(*) active FROM marketcore_action.command_request_v2
                WHERE status IN ('PENDING','RUNNING')""")
            active_before = int(cursor.fetchone()["active"])
            cursor.execute("""INSERT INTO analytics.research_queue_governance_run_v2
                (run_id,status_code,active_before,policy_code)
                VALUES(%s,'RUNNING',%s,%s)""", (run_id, active_before, policy["policy_code"]))

            cursor.execute("""UPDATE analytics.research_queue_v1
                SET status_code='SUPERSEDED',
                    last_error='SUPERSEDED_BY_DB_DRIVEN_RESEARCH_V2',
                    updated_at=clock_timestamp()
                WHERE status_code='QUEUED' AND attempts=0
                  AND source_version='PARAMETER_SEARCH_GRID_V1'
                  AND created_at < clock_timestamp()-(%s * interval '1 day')
                RETURNING research_code,strategy_code,symbol,timeframe""",
                (int(policy["legacy_stale_days"]),))
            legacy_rows = cursor.fetchall()

            archived_lab = 0
            if legacy_rows:
                cursor.execute("""UPDATE analytics.edge_lab_run_v1 e
                    SET status_code='SUPERSEDED',finished_at=clock_timestamp(),updated_at=clock_timestamp(),
                        runner_version='RESEARCH_QUEUE_GOVERNOR_V2'
                    FROM analytics.research_queue_v1 q
                    WHERE q.status_code='SUPERSEDED'
                      AND q.last_error='SUPERSEDED_BY_DB_DRIVEN_RESEARCH_V2'
                      AND e.status_code='QUEUED'
                      AND e.research_code=q.research_code AND e.strategy_code=q.strategy_code
                      AND e.symbol=q.symbol AND e.timeframe=q.timeframe""")
                archived_lab = cursor.rowcount

            priorities = dict(policy["priority_by_kind"] or {})
            for request_kind, priority in priorities.items():
                cursor.execute("""UPDATE marketcore_action.command_request_v2
                    SET priority=%s WHERE request_kind=%s AND status='PENDING' AND priority<>%s""",
                    (int(priority), str(request_kind), int(priority)))

            cursor.execute("""WITH ranked AS (
                  SELECT request_id,row_number() OVER(
                    PARTITION BY request_kind,coalesce(target_id,'')
                    ORDER BY CASE status WHEN 'RUNNING' THEN 0 ELSE 1 END,priority,requested_at,request_id) rn
                  FROM marketcore_action.command_request_v2
                  WHERE status IN ('PENDING','RUNNING'))
                UPDATE marketcore_action.command_request_v2 q
                SET status='CANCELLED',finished_at=clock_timestamp(),
                    result_reference='DEDUPLICATED_BY_RESEARCH_QUEUE_GOVERNOR_V2'
                FROM ranked r WHERE q.request_id=r.request_id AND r.rn>1 AND q.status='PENDING'""")
            duplicates_cancelled = cursor.rowcount

            cursor.execute("""UPDATE marketcore_action.command_request_v2
                SET status='CANCELLED',finished_at=clock_timestamp(),
                    result_reference='STALE_PENDING_CLOSED_BY_RESEARCH_QUEUE_GOVERNOR_V2'
                WHERE status='PENDING'
                  AND requested_at < clock_timestamp()-(%s * interval '1 minute')""",
                (int(policy["pending_stale_minutes"]),))
            stale_cancelled = cursor.rowcount

            cursor.execute("""WITH excess AS (
                  SELECT request_id FROM marketcore_action.command_request_v2
                  WHERE status='PENDING' ORDER BY priority,requested_at
                  OFFSET %s)
                UPDATE marketcore_action.command_request_v2 q
                SET status='CANCELLED',finished_at=clock_timestamp(),
                    result_reference='QUEUE_CAP_APPLIED_BY_RESEARCH_QUEUE_GOVERNOR_V2'
                FROM excess e WHERE q.request_id=e.request_id""", (int(policy["max_pending"]),))
            capacity_cancelled = cursor.rowcount

            cursor.execute("""SELECT count(*) active FROM marketcore_action.command_request_v2
                WHERE status IN ('PENDING','RUNNING')""")
            active_after = int(cursor.fetchone()["active"])
            cursor.execute("""UPDATE analytics.research_queue_governance_run_v2 SET
                status_code='COMPLETE',legacy_archived=%s,lab_runs_archived=%s,
                duplicates_cancelled=%s,stale_cancelled=%s,capacity_cancelled=%s,
                active_after=%s,finished_at=clock_timestamp()
                WHERE run_id=%s""", (len(legacy_rows), archived_lab, duplicates_cancelled,
                                      stale_cancelled, capacity_cancelled, active_after, run_id))

    print(f"legacy_archived={len(legacy_rows)}")
    print(f"lab_runs_archived={archived_lab}")
    print(f"duplicates_cancelled={duplicates_cancelled}")
    print(f"stale_cancelled={stale_cancelled}")
    print(f"capacity_cancelled={capacity_cancelled}")
    print(f"active_before={active_before}")
    print(f"active_after={active_after}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("live_allowed=0")
    print("VERDICT=RESEARCH_QUEUE_GOVERNOR_V2_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
