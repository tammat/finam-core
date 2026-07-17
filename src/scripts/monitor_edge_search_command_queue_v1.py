from __future__ import annotations

import os
import psycopg2

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
    print(f"running_recovered={running_recovered}")
    print(f"pending_expired={pending_expired}")
    print("VERDICT=EDGE_SEARCH_QUEUE_MONITOR_V1_OK")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
