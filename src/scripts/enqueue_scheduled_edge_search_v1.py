from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "EDGE_SEARCH_AUTO_ENQUEUE_V1"
NAMESPACE = uuid.UUID("884b9314-6458-4f49-9a67-382a1e3fe9d8")
LOCK_ID = 741903129


def main() -> int:
    decision = "NO_NEW_MARKET_DATA"
    request_id = None
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("SELECT pg_try_advisory_xact_lock(%s) locked", (LOCK_ID,))
            if not cursor.fetchone()["locked"]:
                print("decision=SCHEDULER_ALREADY_RUNNING")
                print("VERDICT=EDGE_SEARCH_AUTO_ENQUEUE_V1_OK")
                return 0
            cursor.execute("""
                SELECT max(ts) AS watermark
                FROM public.market_bars
                WHERE timeframe='M5' AND source NOT IN ('unknown','synthetic_futures_backfill_v1')
            """)
            watermark = cursor.fetchone()["watermark"]
            cursor.execute("""
                SELECT market_data_watermark
                FROM analytics.edge_search_cycle_status_v1
                WHERE status_code IN ('PASS_FOUND','NO_PASS','NO_CURRENT_MARKETS')
                  AND market_data_watermark IS NOT NULL
                ORDER BY finished_at DESC NULLS LAST,started_at DESC LIMIT 1
            """)
            row = cursor.fetchone()
            evaluated_watermark = row["market_data_watermark"] if row else None
            cursor.execute("""SELECT EXISTS(
                SELECT 1 FROM marketcore_action.command_request_v2
                WHERE request_kind='EDGE_SEARCH_RUN' AND status IN ('PENDING','RUNNING')) active""")
            active = bool(cursor.fetchone()["active"])
            if active:
                decision = "ACTIVE_REQUEST_EXISTS"
            elif watermark is None:
                decision = "NO_TRUSTED_MARKET_DATA"
            elif evaluated_watermark is not None and watermark <= evaluated_watermark:
                decision = "NO_NEW_MARKET_DATA"
            else:
                request_id = str(uuid.uuid5(NAMESPACE, f"{SOURCE_VERSION}:{watermark.isoformat()}"))
                cursor.execute("""
                    INSERT INTO marketcore_action.command_request_v2
                      (request_id,action_id,request_kind,command_code,actor_id,target_id,status,requested_at)
                    VALUES(%s,'research.edge_search.auto','EDGE_SEARCH_RUN','RESEARCH.RUN_EDGE_SEARCH',
                           'system.scheduler',%s,'PENDING',clock_timestamp())
                    ON CONFLICT(request_id) DO NOTHING
                """, (request_id, watermark.isoformat()))
                decision = "ENQUEUED" if cursor.rowcount else "ALREADY_ENQUEUED"
            cursor.execute("""
                INSERT INTO analytics.edge_search_auto_schedule_state_v1
                  (scheduler_code,status_code,decision_code,market_data_watermark,
                   evaluated_watermark,request_id,source_version,updated_at)
                VALUES('EDGE_SEARCH_AUTO','HEALTHY',%s,%s,%s,%s,%s,clock_timestamp())
                ON CONFLICT(scheduler_code) DO UPDATE SET
                  status_code='HEALTHY',decision_code=EXCLUDED.decision_code,
                  market_data_watermark=EXCLUDED.market_data_watermark,
                  evaluated_watermark=EXCLUDED.evaluated_watermark,
                  request_id=EXCLUDED.request_id,source_version=EXCLUDED.source_version,
                  updated_at=clock_timestamp()
            """, (decision,watermark,evaluated_watermark,request_id,SOURCE_VERSION))
    print(f"decision={decision}")
    print(f"request_id={request_id or 'NONE'}")
    print("live_allowed=0")
    print("VERDICT=EDGE_SEARCH_AUTO_ENQUEUE_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
