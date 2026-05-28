from __future__ import annotations

import subprocess

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


TEST_SOURCES = [
    "runtime_governance_live_accumulation_pipeline_final_check_v1",
]


DELETE_SQL = """
DELETE FROM runtime_governance_live_accumulation_v1
WHERE raw_json->>'source' = ANY(%(sources)s);
"""


COUNT_SQL = """
SELECT
    count(*) AS total_rows,
    count(*) FILTER (
        WHERE raw_json->>'source' = ANY(%(sources)s)
    ) AS test_rows,
    max(created_at) AS last_event_ts
FROM runtime_governance_live_accumulation_v1;
"""


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == ""


def read_stats(conn) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            COUNT_SQL,
            {"sources": TEST_SOURCES},
        )
        return dict(cur.fetchone())


def main() -> int:
    print("RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_CLEANUP_V1")

    with psycopg.connect(build_psycopg_url(), row_factory=dict_row) as conn:

        before = read_stats(conn)

        with conn.cursor() as cur:
            cur.execute(
                DELETE_SQL,
                {"sources": TEST_SOURCES},
            )

        conn.commit()

        after = read_stats(conn)

    removed = (
        int(before["test_rows"] or 0)
        - int(after["test_rows"] or 0)
    )

    status = (
        "LIVE_ACCUMULATION_CLEAN"
        if int(after["test_rows"] or 0) == 0
        else "LIVE_ACCUMULATION_TEST_ROWS_LEFT"
    )

    print(
        "RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_CLEANUP_STATUS",
        f"status={status}",
        f"git_clean={git_clean()}",
        f"before_total_rows={before['total_rows']}",
        f"before_test_rows={before['test_rows']}",
        f"after_total_rows={after['total_rows']}",
        f"after_test_rows={after['test_rows']}",
        f"removed_rows={removed}",
        f"last_event_ts={after['last_event_ts']}",
        flush=True,
    )

    print(
        f"RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_CLEANUP_V1_OK status={status}",
        flush=True,
    )

    return 0 if status == "LIVE_ACCUMULATION_CLEAN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
