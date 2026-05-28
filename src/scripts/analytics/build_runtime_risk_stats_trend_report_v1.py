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
),
daily AS (
    SELECT
        event_date,
        count(*) AS total_events,
        count(*) FILTER (WHERE event_class = 'PRODUCTION_CANDIDATE') AS production_events,
        count(*) FILTER (WHERE event_class = 'TEST') AS test_events,
        count(*) FILTER (WHERE event_class = 'UNKNOWN') AS unknown_events,
        count(*) FILTER (WHERE severity = 'CRITICAL') AS critical_events,
        count(*) FILTER (WHERE severity = 'WARNING') AS warning_events,
        count(*) FILTER (WHERE routed = true) AS routed_events,
        count(*) FILTER (WHERE skipped_reason IS NOT NULL) AS skipped_events,
        count(DISTINCT symbol) AS unique_symbols,
        count(DISTINCT strategy) AS unique_strategies,
        count(DISTINCT reason) AS unique_reasons,
        max(created_at) AS last_event_ts
    FROM classified
    GROUP BY event_date
)
"""


TREND_SQL = CLASSIFIED_CTE + """
SELECT
    event_date,
    total_events,
    production_events,
    test_events,
    unknown_events,
    critical_events,
    warning_events,
    routed_events,
    skipped_events,
    unique_symbols,
    unique_strategies,
    unique_reasons,
    last_event_ts,

    lag(total_events) OVER (ORDER BY event_date) AS prev_total_events,
    total_events - coalesce(lag(total_events) OVER (ORDER BY event_date), 0) AS total_delta,

    lag(critical_events) OVER (ORDER BY event_date) AS prev_critical_events,
    critical_events - coalesce(lag(critical_events) OVER (ORDER BY event_date), 0) AS critical_delta

FROM daily
ORDER BY event_date DESC;
"""


TOP_DRIFT_REASON_SQL = CLASSIFIED_CTE + """
SELECT
    event_date,
    reason,
    count(*) AS events,
    count(*) FILTER (WHERE severity = 'CRITICAL') AS critical_events,
    max(created_at) AS last_seen
FROM classified
WHERE event_class = 'PRODUCTION_CANDIDATE'
GROUP BY
    event_date,
    reason
ORDER BY
    event_date DESC,
    events DESC,
    last_seen DESC
LIMIT 20;
"""


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == ""


def status_from(*, git_is_clean: bool, test_events: int, unknown_events: int) -> str:
    if not git_is_clean:
        return "WARN_GIT_DIRTY"

    if unknown_events > 0:
        return "WARN_UNKNOWN_EVENTS"

    if test_events > 0:
        return "WARN_TEST_EVENTS"

    return "OK"


def trend_status(*, total_delta: int, critical_delta: int) -> str:
    if critical_delta >= 5:
        return "CRITICAL_RISK_SPIKE"

    if total_delta >= 5:
        return "RISK_EVENT_SPIKE"

    if total_delta < 0:
        return "RISK_EVENTS_DOWN"

    if total_delta == 0:
        return "STABLE"

    return "RISK_EVENTS_UP"


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(TREND_SQL)
            trend_rows = [dict(r) for r in cur.fetchall()]

            cur.execute(TOP_DRIFT_REASON_SQL)
            reason_rows = [dict(r) for r in cur.fetchall()]

    total_events = sum(int(r["total_events"] or 0) for r in trend_rows)
    total_test = sum(int(r["test_events"] or 0) for r in trend_rows)
    total_unknown = sum(int(r["unknown_events"] or 0) for r in trend_rows)

    git_is_clean = git_clean()
    status = status_from(
        git_is_clean=git_is_clean,
        test_events=total_test,
        unknown_events=total_unknown,
    )

    print("RUNTIME_RISK_STATS_TREND_REPORT_V1", flush=True)

    print(
        "RUNTIME_RISK_STATS_TREND_STATUS",
        f"status={status}",
        f"git_clean={git_is_clean}",
        f"days={len(trend_rows)}",
        f"total_events={total_events}",
        f"test_events={total_test}",
        f"unknown_events={total_unknown}",
        flush=True,
    )

    for row in trend_rows:
        total_delta = int(row["total_delta"] or 0)
        critical_delta = int(row["critical_delta"] or 0)

        print(
            "RUNTIME_RISK_STATS_TREND_ROW",
            f"date={row['event_date']}",
            f"total_events={row['total_events']}",
            f"production_events={row['production_events']}",
            f"critical_events={row['critical_events']}",
            f"warning_events={row['warning_events']}",
            f"routed_events={row['routed_events']}",
            f"skipped_events={row['skipped_events']}",
            f"unique_symbols={row['unique_symbols']}",
            f"unique_strategies={row['unique_strategies']}",
            f"unique_reasons={row['unique_reasons']}",
            f"prev_total_events={row['prev_total_events']}",
            f"total_delta={total_delta}",
            f"critical_delta={critical_delta}",
            f"trend_status={trend_status(total_delta=total_delta, critical_delta=critical_delta)}",
            f"last_event_ts={row['last_event_ts']}",
            flush=True,
        )

    for row in reason_rows:
        print(
            "RUNTIME_RISK_STATS_TREND_REASON_ROW",
            f"date={row['event_date']}",
            f"reason={row['reason']}",
            f"events={row['events']}",
            f"critical_events={row['critical_events']}",
            f"last_seen={row['last_seen']}",
            flush=True,
        )

    print(
        "RUNTIME_RISK_STATS_TREND_REPORT_V1_OK",
        f"status={status}",
        f"days={len(trend_rows)}",
        f"reason_rows={len(reason_rows)}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
