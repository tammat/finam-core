from __future__ import annotations

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


SUMMARY_SQL = """
SELECT
    count(*) AS total_rows,

    count(*) FILTER (
        WHERE severity = 'CRITICAL'
    ) AS critical_rows,

    count(*) FILTER (
        WHERE routed = true
    ) AS routed_rows,

    count(*) FILTER (
        WHERE skipped_reason IS NOT NULL
    ) AS skipped_rows

FROM risk_event_audit_v1;
"""


DETAIL_SQL = """
SELECT
    symbol,
    severity,
    decision,
    reason,
    routed,
    channel,
    skipped_reason,
    count(*) AS events,
    max(created_at) AS last_seen
FROM risk_event_audit_v1
GROUP BY
    symbol,
    severity,
    decision,
    reason,
    routed,
    channel,
    skipped_reason
ORDER BY
    events DESC,
    last_seen DESC
LIMIT 50;
"""


def main() -> None:
    print("RISK_EVENT_AUDIT_SUMMARY_V1", flush=True)

    database_url = build_psycopg_url()

    with psycopg.connect(
        database_url,
        row_factory=dict_row,
    ) as conn:

        with conn.cursor() as cur:
            cur.execute(SUMMARY_SQL)
            summary = cur.fetchone()

        print(
            "RISK_EVENT_AUDIT_SUMMARY",
            f"total_rows={summary['total_rows']}",
            f"critical_rows={summary['critical_rows']}",
            f"routed_rows={summary['routed_rows']}",
            f"skipped_rows={summary['skipped_rows']}",
            flush=True,
        )

        with conn.cursor() as cur:
            cur.execute(DETAIL_SQL)

            rows = cur.fetchall()

        for row in rows:
            print(
                "RISK_EVENT_AUDIT_ROW",
                f"symbol={row['symbol']}",
                f"severity={row['severity']}",
                f"decision={row['decision']}",
                f"reason={row['reason']}",
                f"routed={row['routed']}",
                f"channel={row['channel']}",
                f"skipped_reason={row['skipped_reason']}",
                f"events={row['events']}",
                f"last_seen={row['last_seen']}",
                flush=True,
            )

    print(
        "RISK_EVENT_AUDIT_SUMMARY_V1_OK",
        f"rows={len(rows)}",
        flush=True,
    )


if __name__ == "__main__":
    main()
