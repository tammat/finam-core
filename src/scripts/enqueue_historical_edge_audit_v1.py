from __future__ import annotations

import os
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE = "HISTORICAL_EDGE_AUDIT_ENQUEUE_V1"
NAMESPACE = uuid.UUID("154f765e-0ca0-4cc7-8ead-85a3c025c6e1")


def main() -> int:
    day = datetime.now(ZoneInfo("Europe/Moscow")).date().isoformat()
    request_id = str(uuid.uuid5(NAMESPACE, f"{SOURCE}:{day}"))
    process_id = uuid.UUID(request_id)
    decision = "ALREADY_ENQUEUED"
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""SELECT EXISTS(SELECT 1 FROM marketcore_action.command_request_v2
                WHERE request_kind='EDGE_SEARCH_RUN' AND status IN ('PENDING','RUNNING')) active""")
            if cursor.fetchone()["active"]:
                decision = "ACTIVE_REQUEST_EXISTS"
            else:
                cursor.execute("""INSERT INTO marketcore_action.research_process_v1(
                    process_id,process_type,recommendation_code,command_request_id,status_code,
                    progress_pct,current_step_code,reason_code,explanation_ru,actor_id)
                    VALUES(%s,'EDGE_SEARCH','KEEP_GATES_AND_EXPAND_EVIDENCE',%s,'PENDING',0,
                           'QUEUED','HISTORICAL_AUDIT_SCHEDULED',
                           'Полный исторический цикл поставлен системой в очередь.','system.historical_audit')
                    ON CONFLICT(process_id) DO NOTHING""", (str(process_id),request_id))
                cursor.execute("""INSERT INTO marketcore_action.command_request_v2(
                    request_id,action_id,request_kind,command_code,actor_id,target_id,status,
                    requested_at,process_id,priority)
                    VALUES(%s,'research.edge_search.historical','EDGE_SEARCH_RUN','RESEARCH.RUN_EDGE_SEARCH',
                           'system.historical_audit',%s,'PENDING',clock_timestamp(),%s,35)
                    ON CONFLICT(request_id) DO NOTHING""", (request_id,day,str(process_id)))
                decision = "ENQUEUED" if cursor.rowcount else "ALREADY_ENQUEUED"
            cursor.execute("""INSERT INTO analytics.historical_edge_audit_schedule_state_v1(
                scheduler_code,status_code,decision_code,request_id,last_attempt_at,last_enqueued_at,
                source_version,updated_at)
                VALUES('HISTORICAL_EDGE_AUDIT','HEALTHY',%s,%s,clock_timestamp(),
                       CASE WHEN %s='ENQUEUED' THEN clock_timestamp() END,%s,clock_timestamp())
                ON CONFLICT(scheduler_code) DO UPDATE SET status_code='HEALTHY',
                  decision_code=excluded.decision_code,request_id=excluded.request_id,
                  last_attempt_at=excluded.last_attempt_at,
                  last_enqueued_at=coalesce(excluded.last_enqueued_at,
                    analytics.historical_edge_audit_schedule_state_v1.last_enqueued_at),
                  last_error_code=NULL,source_version=excluded.source_version,updated_at=clock_timestamp()""",
                (decision,request_id,decision,SOURCE))
    print(f"decision={decision}")
    print(f"request_id={request_id}")
    print("live_allowed=0")
    print("VERDICT=HISTORICAL_EDGE_AUDIT_ENQUEUE_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
