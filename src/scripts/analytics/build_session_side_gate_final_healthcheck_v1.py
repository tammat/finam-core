from __future__ import annotations

import os
import subprocess

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


SUMMARY_SQL = """
SELECT
    count(*) AS total_events,

    count(*) FILTER (
        WHERE allowed = true
    ) AS allowed_events,

    count(*) FILTER (
        WHERE allowed = false
    ) AS blocked_events,

    count(*) FILTER (
        WHERE source ILIKE '%test%'
    ) AS test_events,

    count(*) FILTER (
        WHERE raw_json::text ILIKE '%test%'
    ) AS raw_test_events,

    count(DISTINCT symbol) AS unique_symbols,
    count(DISTINCT side) AS unique_sides,
    count(DISTINCT reason) AS unique_reasons,

    max(created_at) AS last_event_ts

FROM session_side_gate_runtime_audit_v1;
"""


LAST_SQL = """
SELECT
    id,
    created_at,
    symbol,
    side,
    hour_msk,
    session_name,
    action,
    allowed,
    reason,
    source
FROM session_side_gate_runtime_audit_v1
ORDER BY id DESC
LIMIT 5;
"""


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == ""


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(SUMMARY_SQL)
            summary = dict(cur.fetchone())

            cur.execute(LAST_SQL)
            rows = [dict(r) for r in cur.fetchall()]

    status = "OK"

    if not git_clean():
        status = "WARN_GIT_DIRTY"

    elif int(summary["test_events"] or 0) > 0:
        status = "WARN_TEST_EVENTS"

    elif int(summary["raw_test_events"] or 0) > 0:
        status = "WARN_RAW_TEST_EVENTS"

    print("SESSION_SIDE_GATE_FINAL_HEALTHCHECK_V1", flush=True)

    print(
        "SESSION_SIDE_GATE_FINAL_HEALTHCHECK_STATUS",
        f"status={status}",
        f"git_clean={git_clean()}",
        f"total_events={summary['total_events']}",
        f"allowed_events={summary['allowed_events']}",
        f"blocked_events={summary['blocked_events']}",
        f"test_events={summary['test_events']}",
        f"raw_test_events={summary['raw_test_events']}",
        f"unique_symbols={summary['unique_symbols']}",
        f"unique_sides={summary['unique_sides']}",
        f"unique_reasons={summary['unique_reasons']}",
        f"last_event_ts={summary['last_event_ts']}",
        flush=True,
    )

    for row in rows:
        print(
            "SESSION_SIDE_GATE_FINAL_HEALTHCHECK_LAST_EVENT",
            f"id={row['id']}",
            f"ts={row['created_at']}",
            f"symbol={row['symbol']}",
            f"side={row['side']}",
            f"hour_msk={row['hour_msk']}",
            f"session={row['session_name']}",
            f"action={row['action']}",
            f"allowed={row['allowed']}",
            f"reason={row['reason']}",
            f"source={row['source']}",
            flush=True,
        )

    print(
        "SESSION_SIDE_GATE_FINAL_HEALTHCHECK_V1_OK",
        f"status={status}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
