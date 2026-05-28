from __future__ import annotations

import subprocess

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


DELETE_SQL = """
DELETE FROM runtime_shadow_observation_v1
WHERE raw_json->>'source' = 'runtime_shadow_observation_persistence_v1';
"""


COUNT_SQL = """
SELECT count(*) AS rows_count
FROM runtime_shadow_observation_v1;
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
    url = build_psycopg_url()

    with psycopg.connect(url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(DELETE_SQL)
            deleted = cur.rowcount

            cur.execute(COUNT_SQL)
            remaining = int(cur.fetchone()["rows_count"])

        conn.commit()

    status = "OK" if git_clean() else "WARN_GIT_DIRTY"

    print("RUNTIME_SHADOW_OBSERVATION_CLEANUP_TEST_ROWS_V1", flush=True)

    print(
        "RUNTIME_SHADOW_OBSERVATION_CLEANUP_STATUS",
        f"status={status}",
        f"deleted_rows={deleted}",
        f"remaining_rows={remaining}",
        flush=True,
    )

    print(
        "RUNTIME_SHADOW_OBSERVATION_CLEANUP_TEST_ROWS_V1_OK",
        f"status={status}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
