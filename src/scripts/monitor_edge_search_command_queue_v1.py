from __future__ import annotations

import os
import psycopg2
import uuid

DB=os.getenv("DATABASE_URL","postgresql:///finam_core")


def main() -> int:
    with psycopg2.connect(DB) as connection:
        with connection.cursor() as cursor:
            cursor.execute("""UPDATE marketcore_action.command_request_v2
                SET status='FAILED',finished_at=clock_timestamp(),failure_code='EDGE_SEARCH_RUNNING_TIMEOUT'
                WHERE request_kind='EDGE_SEARCH_RUN' AND status='RUNNING'
                  AND started_at<clock_timestamp()-interval '2 hours'""")
            running_recovered=cursor.rowcount
            cursor.execute("""UPDATE marketcore_action.command_request_v2
                SET status='FAILED',finished_at=clock_timestamp(),failure_code='EDGE_SEARCH_PENDING_EXPIRED'
                WHERE request_kind='EDGE_SEARCH_RUN' AND status='PENDING'
                  AND requested_at<clock_timestamp()-interval '24 hours'""")
            pending_expired=cursor.rowcount
            cursor.execute("""SELECT q.* FROM marketcore_action.command_request_v2 q
                LEFT JOIN marketcore_action.edge_search_retry_v1 r ON r.source_request_id=q.request_id
                WHERE q.request_kind='EDGE_SEARCH_RUN' AND q.status='FAILED' AND r.source_request_id IS NULL
                  AND NOT EXISTS(
                    SELECT 1 FROM marketcore_action.edge_search_retry_v1 parent_retry
                    WHERE parent_retry.retry_request_id=q.request_id
                  )
                  AND q.failure_code LIKE 'WORKER_COMMAND_FAILED:%'
                  AND NOT EXISTS(SELECT 1 FROM marketcore_action.command_request_v2
                                 WHERE request_kind='EDGE_SEARCH_RUN' AND status IN ('PENDING','RUNNING'))
                ORDER BY q.finished_at DESC LIMIT 1""")
            failed=cursor.fetchone(); retry_created=0
            if failed:
                retry_id=str(uuid.uuid4())
                cursor.execute("""INSERT INTO marketcore_action.command_request_v2
                    (request_id,action_id,request_kind,command_code,actor_id,target_id,status,requested_at)
                    VALUES(%s,%s,'EDGE_SEARCH_RUN','RESEARCH.RUN_EDGE_SEARCH',%s,%s,'PENDING',clock_timestamp())""",
                    (retry_id,failed[1],failed[4],failed[11]))
                cursor.execute("INSERT INTO marketcore_action.edge_search_retry_v1 VALUES(%s,%s,%s,clock_timestamp())",
                               (failed[0],retry_id,failed[10]))
                retry_created=1
    print(f"running_recovered={running_recovered}")
    print(f"pending_expired={pending_expired}")
    print(f"technical_retry_created={retry_created}")
    print("VERDICT=EDGE_SEARCH_QUEUE_MONITOR_V1_OK")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
