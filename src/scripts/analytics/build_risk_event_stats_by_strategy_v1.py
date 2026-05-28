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
        skipped_reason,

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
    strategy,
    timeframe,

    count(*) AS total_events,

    count(*) FILTER (
        WHERE severity = 'CRITICAL'
    ) AS critical_events,

    count(*) FILTER (
        WHERE severity = 'WARNING'
    ) AS warning_events,

    count(*) FILTER (
        WHERE event_class = 'PRODUCTION_CANDIDATE'
    ) AS production_events,

    count(*) FILTER (
        WHERE event_class = 'TEST'
    ) AS test_events,

    count(*) FILTER (
        WHERE event_class = 'UNKNOWN'
    ) AS unknown_events,

    count(*) FILTER (
        WHERE routed = true
    ) AS routed_events,

    count(*) FILTER (
        WHERE skipped_reason IS NOT NULL
    ) AS skipped_events,

    count(DISTINCT symbol) AS unique_symbols,
    count(DISTINCT reason) AS unique_reasons,

    min(created_at) AS first_seen,
    max(created_at) AS last_seen

FROM classified

GROUP BY
    strategy,
    timeframe

ORDER BY
    total_events DESC,
    last_seen DESC;
"""


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
            rows = cur.fetchall()

    total_events = sum(int(r["total_events"]) for r in rows)

    print("RISK_EVENT_STATS_BY_STRATEGY_V1", flush=True)
    print(
        "RISK_EVENT_STATS_BY_STRATEGY_SUMMARY",
        f"strategies={len(rows)}",
        f"total_events={total_events}",
        flush=True,
    )

    for row in rows:
        print(
            "RISK_EVENT_STATS_BY_STRATEGY_ROW",
            f"strategy={row['strategy']}",
            f"timeframe={row['timeframe']}",
            f"total_events={row['total_events']}",
            f"critical_events={row['critical_events']}",
            f"warning_events={row['warning_events']}",
            f"production_events={row['production_events']}",
            f"test_events={row['test_events']}",
            f"unknown_events={row['unknown_events']}",
            f"routed_events={row['routed_events']}",
            f"skipped_events={row['skipped_events']}",
            f"unique_symbols={row['unique_symbols']}",
            f"unique_reasons={row['unique_reasons']}",
            f"first_seen={row['first_seen']}",
            f"last_seen={row['last_seen']}",
            flush=True,
        )

    print(
        "RISK_EVENT_STATS_BY_STRATEGY_V1_OK",
        f"rows={len(rows)}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
