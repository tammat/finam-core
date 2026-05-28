from __future__ import annotations

import os
import subprocess

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


SQL = """
SELECT
    action,
    allowed,
    reason,
    source,
    count(*) AS events,
    count(DISTINCT symbol) AS symbols,
    count(DISTINCT side) AS sides,
    min(created_at) AS first_seen,
    max(created_at) AS last_seen
FROM session_side_gate_runtime_audit_v1
GROUP BY
    action,
    allowed,
    reason,
    source
ORDER BY
    events DESC,
    last_seen DESC;
"""


TOTAL_SQL = """
SELECT
    count(*) AS total_events,
    count(*) FILTER (WHERE allowed = true) AS allowed_events,
    count(*) FILTER (WHERE allowed = false) AS blocked_events,
    count(*) FILTER (WHERE source ILIKE '%test%') AS test_events,
    max(created_at) AS last_event_ts
FROM session_side_gate_runtime_audit_v1;
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
            cur.execute(TOTAL_SQL)
            total = dict(cur.fetchone())

            cur.execute(SQL)
            rows = [dict(r) for r in cur.fetchall()]

    status = "OK"
    if not git_clean():
        status = "WARN_GIT_DIRTY"
    elif int(total["test_events"] or 0) > 0:
        status = "WARN_TEST_EVENTS"

    print("SESSION_SIDE_GATE_RUNTIME_AUDIT_SUMMARY_V1", flush=True)
    print(
        "SESSION_SIDE_GATE_RUNTIME_AUDIT_SUMMARY_STATUS",
        f"status={status}",
        f"git_clean={git_clean()}",
        f"total_events={total['total_events']}",
        f"allowed_events={total['allowed_events']}",
        f"blocked_events={total['blocked_events']}",
        f"test_events={total['test_events']}",
        f"last_event_ts={total['last_event_ts']}",
        flush=True,
    )

    for row in rows:
        print(
            "SESSION_SIDE_GATE_RUNTIME_AUDIT_SUMMARY_ROW",
            f"action={row['action']}",
            f"allowed={row['allowed']}",
            f"reason={row['reason']}",
            f"source={row['source']}",
            f"events={row['events']}",
            f"symbols={row['symbols']}",
            f"sides={row['sides']}",
            f"first_seen={row['first_seen']}",
            f"last_seen={row['last_seen']}",
            flush=True,
        )

    print(
        "SESSION_SIDE_GATE_RUNTIME_AUDIT_SUMMARY_V1_OK",
        f"status={status}",
        f"rows={len(rows)}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
