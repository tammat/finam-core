from __future__ import annotations

import os

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


SQL = """
WITH classified AS (
    SELECT
        id,
        created_at,
        category,
        severity,
        symbol,
        strategy,
        timeframe,
        decision,
        reason,
        routed,
        channel,
        skipped_reason,
        raw_json,
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
    event_class,
    category,
    severity,
    symbol,
    decision,
    reason,
    routed,
    channel,
    skipped_reason,
    count(*) AS events,
    max(created_at) AS last_seen
FROM classified
GROUP BY
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
    CASE event_class
        WHEN 'PRODUCTION_CANDIDATE' THEN 1
        WHEN 'UNKNOWN' THEN 2
        WHEN 'TEST' THEN 3
        ELSE 4
    END,
    events DESC,
    last_seen DESC;
"""


SUMMARY_SQL = """
WITH classified AS (
    SELECT
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
    count(*) AS total_rows,
    count(*) FILTER (WHERE event_class = 'PRODUCTION_CANDIDATE') AS production_candidate_rows,
    count(*) FILTER (WHERE event_class = 'TEST') AS test_rows,
    count(*) FILTER (WHERE event_class = 'UNKNOWN') AS unknown_rows
FROM classified;
"""


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(SUMMARY_SQL)
            summary = dict(cur.fetchone())

            cur.execute(SQL)
            rows = [dict(r) for r in cur.fetchall()]

    print("RISK_EVENT_AUDIT_PRODUCTION_FILTER_V1", flush=True)

    print(
        "RISK_EVENT_AUDIT_PRODUCTION_FILTER_SUMMARY",
        f"total_rows={summary['total_rows']}",
        f"production_candidate_rows={summary['production_candidate_rows']}",
        f"test_rows={summary['test_rows']}",
        f"unknown_rows={summary['unknown_rows']}",
        flush=True,
    )

    for r in rows:
        print(
            "RISK_EVENT_AUDIT_PRODUCTION_FILTER_ROW",
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
            f"last_seen={r['last_seen']}",
            flush=True,
        )

    print(f"RISK_EVENT_AUDIT_PRODUCTION_FILTER_V1_OK rows={len(rows)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
