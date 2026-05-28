from __future__ import annotations

import os
import subprocess

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
    count(*) AS total_events,
    count(*) FILTER (WHERE event_class = 'PRODUCTION_CANDIDATE') AS production_events,
    count(*) FILTER (WHERE event_class = 'TEST') AS test_events,
    count(*) FILTER (WHERE event_class = 'UNKNOWN') AS unknown_events,
    count(*) FILTER (WHERE severity = 'CRITICAL') AS critical_events,
    count(*) FILTER (WHERE severity = 'WARNING') AS warning_events,
    count(*) FILTER (WHERE routed = true) AS routed_events,
    count(*) FILTER (WHERE skipped_reason IS NOT NULL) AS skipped_events,
    count(DISTINCT reason) AS unique_reasons,
    count(DISTINCT symbol) AS unique_symbols,
    count(DISTINCT strategy) AS unique_strategies,
    max(created_at) AS last_event_ts
FROM classified;
"""


def git_clean() -> bool:
    r = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return r.stdout.strip() == ""


def status(row: dict, clean: bool) -> str:
    if not clean:
        return "WARN_GIT_DIRTY"
    if int(row["test_events"] or 0) > 0:
        return "WARN_TEST_EVENTS"
    if int(row["unknown_events"] or 0) > 0:
        return "WARN_UNKNOWN_EVENTS"
    if int(row["total_events"] or 0) <= 0:
        return "WARN_NO_EVENTS"
    return "OK"


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
            row = dict(cur.fetchone())

    clean = git_clean()
    result_status = status(row, clean)

    print("RISK_EVENT_STATS_FINAL_CHECK_V1", flush=True)
    print(
        "RISK_EVENT_STATS_FINAL_CHECK_STATUS",
        f"status={result_status}",
        f"git_clean={clean}",
        f"total_events={row['total_events']}",
        f"production_events={row['production_events']}",
        f"test_events={row['test_events']}",
        f"unknown_events={row['unknown_events']}",
        f"critical_events={row['critical_events']}",
        f"warning_events={row['warning_events']}",
        f"routed_events={row['routed_events']}",
        f"skipped_events={row['skipped_events']}",
        f"unique_reasons={row['unique_reasons']}",
        f"unique_symbols={row['unique_symbols']}",
        f"unique_strategies={row['unique_strategies']}",
        f"last_event_ts={row['last_event_ts']}",
        flush=True,
    )
    print("RISK_EVENT_STATS_FINAL_CHECK_V1_OK", f"status={result_status}", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
