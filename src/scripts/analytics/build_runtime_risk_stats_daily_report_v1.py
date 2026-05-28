from __future__ import annotations

import os
import subprocess

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


CLASSIFIED_CTE = """
WITH classified AS (
    SELECT
        id,
        created_at,
        (created_at AT TIME ZONE 'Europe/Moscow')::date AS event_date,
        severity,
        symbol,
        strategy,
        timeframe,
        decision,
        reason,
        routed,
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
"""


SUMMARY_SQL = CLASSIFIED_CTE + """
SELECT
    event_date,

    count(*) AS total_events,

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
        WHERE severity = 'CRITICAL'
    ) AS critical_events,

    count(*) FILTER (
        WHERE severity = 'WARNING'
    ) AS warning_events,

    count(*) FILTER (
        WHERE routed = true
    ) AS routed_events,

    count(*) FILTER (
        WHERE skipped_reason IS NOT NULL
    ) AS skipped_events,

    count(DISTINCT symbol) AS unique_symbols,

    count(DISTINCT strategy) AS unique_strategies,

    count(DISTINCT reason) AS unique_reasons,

    max(created_at) AS last_event_ts

FROM classified

GROUP BY event_date

ORDER BY event_date DESC;
"""


TOP_REASON_SQL = CLASSIFIED_CTE + """
SELECT
    event_date,
    reason,
    count(*) AS events,
    max(created_at) AS last_seen
FROM classified
GROUP BY
    event_date,
    reason
ORDER BY
    events DESC,
    last_seen DESC
LIMIT 5;
"""


TOP_SYMBOL_SQL = CLASSIFIED_CTE + """
SELECT
    event_date,
    symbol,
    strategy,
    count(*) AS events,
    max(created_at) AS last_seen
FROM classified
GROUP BY
    event_date,
    symbol,
    strategy
ORDER BY
    events DESC,
    last_seen DESC
LIMIT 5;
"""


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )

    return not bool(result.stdout.strip())


def build_status(
    *,
    git_is_clean: bool,
    unknown_events: int,
    test_events: int,
) -> str:
    if not git_is_clean:
        return "WARN_GIT_DIRTY"

    if unknown_events > 0:
        return "WARN_UNKNOWN_EVENTS"

    if test_events > 0:
        return "WARN_TEST_EVENTS"

    return "OK"


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(
        database_url,
        row_factory=dict_row,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(SUMMARY_SQL)
            summary_rows = cur.fetchall()

            cur.execute(TOP_REASON_SQL)
            top_reason_rows = cur.fetchall()

            cur.execute(TOP_SYMBOL_SQL)
            top_symbol_rows = cur.fetchall()

    total_events = sum(
        int(r["total_events"])
        for r in summary_rows
    )

    total_unknown = sum(
        int(r["unknown_events"])
        for r in summary_rows
    )

    total_test = sum(
        int(r["test_events"])
        for r in summary_rows
    )

    git_is_clean = git_clean()

    status = build_status(
        git_is_clean=git_is_clean,
        unknown_events=total_unknown,
        test_events=total_test,
    )

    print(
        "RUNTIME_RISK_STATS_DAILY_REPORT_V1",
        flush=True,
    )

    print(
        "RUNTIME_RISK_STATS_DAILY_REPORT_STATUS "
        f"status={status} "
        f"git_clean={git_is_clean} "
        f"days={len(summary_rows)} "
        f"total_events={total_events} "
        f"unknown_events={total_unknown} "
        f"test_events={total_test}",
        flush=True,
    )

    for row in summary_rows:
        print(
            "RUNTIME_RISK_STATS_DAILY_ROW "
            f"date={row['event_date']} "
            f"total_events={row['total_events']} "
            f"production_events={row['production_events']} "
            f"test_events={row['test_events']} "
            f"unknown_events={row['unknown_events']} "
            f"critical_events={row['critical_events']} "
            f"warning_events={row['warning_events']} "
            f"routed_events={row['routed_events']} "
            f"skipped_events={row['skipped_events']} "
            f"unique_symbols={row['unique_symbols']} "
            f"unique_strategies={row['unique_strategies']} "
            f"unique_reasons={row['unique_reasons']} "
            f"last_event_ts={row['last_event_ts']}",
            flush=True,
        )

    for row in top_reason_rows:
        print(
            "RUNTIME_RISK_STATS_TOP_REASON "
            f"date={row['event_date']} "
            f"reason={row['reason']} "
            f"events={row['events']} "
            f"last_seen={row['last_seen']}",
            flush=True,
        )

    for row in top_symbol_rows:
        print(
            "RUNTIME_RISK_STATS_TOP_SYMBOL "
            f"date={row['event_date']} "
            f"symbol={row['symbol']} "
            f"strategy={row['strategy']} "
            f"events={row['events']} "
            f"last_seen={row['last_seen']}",
            flush=True,
        )

    print(
        "RUNTIME_RISK_STATS_DAILY_REPORT_V1_OK "
        f"status={status} "
        f"days={len(summary_rows)}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
