from __future__ import annotations

import os

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


SUMMARY_SQL = """
WITH classified AS (
    SELECT
        (created_at AT TIME ZONE 'Europe/Moscow')::date AS event_date,
        category,
        severity,
        symbol,
        decision,
        reason,
        routed,
        channel,
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
)
SELECT
    event_date,
    event_class,
    category,
    severity,
    symbol,
    decision,
    reason,
    routed,
    channel,
    skipped_reason,
    count(*) AS events
FROM classified
GROUP BY
    event_date,
    event_class,
    category,
    severity,
    symbol,
    decision,
    reason,
    routed,
    channel,
    skipped_reason
ORDER BY
    event_date DESC,
    CASE event_class
        WHEN 'PRODUCTION_CANDIDATE' THEN 1
        WHEN 'UNKNOWN' THEN 2
        WHEN 'TEST' THEN 3
        ELSE 4
    END,
    events DESC,
    symbol,
    reason;
"""


TOTAL_SQL = """
WITH classified AS (
    SELECT
        (created_at AT TIME ZONE 'Europe/Moscow')::date AS event_date,
        CASE
            WHEN raw_json::text ILIKE '%"test"%'
              OR raw_json::text ILIKE '%wire_%'
              OR reason ILIKE '%test%'
                THEN 'TEST'
            WHEN raw_json->>'source' = 'risk_notification_bridge_v1'
                THEN 'PRODUCTION_CANDIDATE'
            ELSE 'UNKNOWN'
        END AS event_class,
        severity,
        routed,
        skipped_reason
    FROM risk_event_audit_v1
)
SELECT
    event_date,
    count(*) AS total_events,
    count(*) FILTER (WHERE event_class = 'PRODUCTION_CANDIDATE') AS production_candidate_events,
    count(*) FILTER (WHERE event_class = 'TEST') AS test_events,
    count(*) FILTER (WHERE event_class = 'UNKNOWN') AS unknown_events,
    count(*) FILTER (WHERE severity = 'CRITICAL') AS critical_events,
    count(*) FILTER (WHERE severity = 'WARNING') AS warning_events,
    count(*) FILTER (WHERE routed = true) AS routed_events,
    count(*) FILTER (WHERE skipped_reason IS NOT NULL) AS skipped_events
FROM classified
GROUP BY event_date
ORDER BY event_date DESC;
"""


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(TOTAL_SQL)
            totals = [dict(r) for r in cur.fetchall()]

            cur.execute(SUMMARY_SQL)
            rows = [dict(r) for r in cur.fetchall()]

    print("RISK_EVENT_AUDIT_DAILY_SUMMARY_V1", flush=True)

    for r in totals:
        print(
            "RISK_EVENT_AUDIT_DAILY_TOTAL",
            f"date={r['event_date']}",
            f"total={r['total_events']}",
            f"production_candidate={r['production_candidate_events']}",
            f"test={r['test_events']}",
            f"unknown={r['unknown_events']}",
            f"critical={r['critical_events']}",
            f"warning={r['warning_events']}",
            f"routed={r['routed_events']}",
            f"skipped={r['skipped_events']}",
            flush=True,
        )

    for r in rows:
        print(
            "RISK_EVENT_AUDIT_DAILY_ROW",
            f"date={r['event_date']}",
            f"class={r['event_class']}",
            f"category={r['category']}",
            f"severity={r['severity']}",
            f"symbol={r['symbol']}",
            f"decision={r['decision']}",
            f"reason={r['reason']}",
            f"routed={r['routed']}",
            f"channel={r['channel']}",
            f"skipped_reason={r['skipped_reason']}",
            f"events={r['events']}",
            flush=True,
        )

    print(
        "RISK_EVENT_AUDIT_DAILY_SUMMARY_V1_OK",
        f"days={len(totals)}",
        f"rows={len(rows)}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
