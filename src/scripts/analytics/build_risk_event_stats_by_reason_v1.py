from __future__ import annotations

import os

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


SQL = """
WITH classified AS (
    SELECT
        created_at,
        severity,
        symbol,
        strategy,
        timeframe,
        decision,
        reason,
        routed,
        channel,

        CASE
            WHEN position('"test"' in raw_json::text) > 0
              OR position('wire_' in raw_json::text) > 0
              OR position('test' in lower(reason)) > 0
                THEN 'TEST'

            WHEN raw_json->>'source' = 'risk_notification_bridge_v1'
                THEN 'PRODUCTION_CANDIDATE'

            ELSE 'UNKNOWN'
        END AS event_class

    FROM risk_event_audit_v1
)

SELECT
    reason,
    severity,
    decision,

    count(*) AS total_events,

    count(*) FILTER (
        WHERE event_class = 'PRODUCTION_CANDIDATE'
    ) AS production_events,

    count(*) FILTER (
        WHERE routed = true
    ) AS routed_events,

    count(DISTINCT symbol) AS unique_symbols,

    min(created_at) AS first_seen,
    max(created_at) AS last_seen

FROM classified

GROUP BY
    reason,
    severity,
    decision

ORDER BY
    total_events DESC,
    last_seen DESC;
"""


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(
        database_url,
        row_factory=dict_row,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
            rows = cur.fetchall()

    print("RISK_EVENT_STATS_BY_REASON_V1", flush=True)

    if not rows:
        print(
            "RISK_EVENT_STATS_BY_REASON_EMPTY",
            flush=True,
        )

        print(
            "RISK_EVENT_STATS_BY_REASON_V1_OK rows=0",
            flush=True,
        )

        return 0

    total_events = sum(int(r["total_events"]) for r in rows)

    print(
        f"RISK_EVENT_STATS_BY_REASON_SUMMARY "
        f"reasons={len(rows)} "
        f"total_events={total_events}",
        flush=True,
    )

    for row in rows:
        print(
            f"RISK_EVENT_STATS_BY_REASON_ROW "
            f"reason={row['reason']} "
            f"severity={row['severity']} "
            f"decision={row['decision']} "
            f"total_events={row['total_events']} "
            f"production_events={row['production_events']} "
            f"routed_events={row['routed_events']} "
            f"unique_symbols={row['unique_symbols']} "
            f"first_seen={row['first_seen']} "
            f"last_seen={row['last_seen']}",
            flush=True,
        )

    print(
        f"RISK_EVENT_STATS_BY_REASON_V1_OK rows={len(rows)}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
