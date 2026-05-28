from __future__ import annotations

import os

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


HEALTHCHECK_SQL = """
WITH classified AS (
    SELECT
        created_at,
        severity,
        routed,
        skipped_reason,
        CASE
            WHEN raw_json::text ILIKE '%"test"%'
              OR raw_json::text ILIKE '%wire_%'
              OR reason ILIKE '%test%'
                THEN 'TEST'
            WHEN raw_json->>'source' = 'risk_notification_bridge_v1'
                THEN 'PRODUCTION_CANDIDATE'
            ELSE 'UNKNOWN'
        END AS event_class
    FROM risk_event_audit_v1
),
today_rows AS (
    SELECT *
    FROM classified
    WHERE
        (created_at AT TIME ZONE 'Europe/Moscow')::date =
        (now() AT TIME ZONE 'Europe/Moscow')::date
)
SELECT
    count(*) AS total_today,
    count(*) FILTER (WHERE severity = 'CRITICAL') AS critical_today,
    count(*) FILTER (WHERE event_class = 'TEST') AS test_rows_today,
    count(*) FILTER (WHERE event_class = 'UNKNOWN') AS unknown_rows_today,
    count(*) FILTER (WHERE routed = true) AS routed_today,
    count(*) FILTER (WHERE skipped_reason IS NOT NULL) AS skipped_today,
    max(created_at) AS last_event_ts
FROM today_rows;
"""


def determine_status(*, unknown_rows: int, last_event_ts: str | None) -> str:
    if unknown_rows > 0:
        return "WARN"

    if last_event_ts is None:
        return "WARN"

    return "OK"


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(HEALTHCHECK_SQL)
            row = dict(cur.fetchone())

    total_today = int(row["total_today"] or 0)
    critical_today = int(row["critical_today"] or 0)
    test_rows_today = int(row["test_rows_today"] or 0)
    unknown_rows_today = int(row["unknown_rows_today"] or 0)
    routed_today = int(row["routed_today"] or 0)
    skipped_today = int(row["skipped_today"] or 0)

    last_event_ts = str(row["last_event_ts"]) if row["last_event_ts"] is not None else None

    status = determine_status(
        unknown_rows=unknown_rows_today,
        last_event_ts=last_event_ts,
    )

    print("RISK_EVENT_AUDIT_HEALTHCHECK_V1", flush=True)
    print(
        "RISK_EVENT_AUDIT_HEALTHCHECK_STATUS",
        f"status={status}",
        f"total_today={total_today}",
        f"critical_today={critical_today}",
        f"test_rows_today={test_rows_today}",
        f"unknown_rows_today={unknown_rows_today}",
        f"routed_today={routed_today}",
        f"skipped_today={skipped_today}",
        f"last_event_ts={last_event_ts}",
        flush=True,
    )
    print("RISK_EVENT_AUDIT_HEALTHCHECK_V1_OK", f"status={status}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
