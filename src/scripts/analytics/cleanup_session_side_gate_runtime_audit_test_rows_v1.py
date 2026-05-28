from __future__ import annotations

import os

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


SQL = """
DELETE FROM session_side_gate_runtime_audit_v1
WHERE
    source ILIKE '%test%'
    OR raw_json::text LIKE '%"test"%'
RETURNING id;
"""


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
            rows = [dict(r) for r in cur.fetchall()]
        conn.commit()

    deleted_ids = ",".join(str(r["id"]) for r in rows)

    print("SESSION_SIDE_GATE_RUNTIME_AUDIT_CLEANUP_TEST_ROWS_V1", flush=True)
    print(
        "SESSION_SIDE_GATE_RUNTIME_AUDIT_CLEANUP_RESULT",
        f"deleted={len(rows)}",
        f"deleted_ids={deleted_ids}",
        flush=True,
    )
    print("SESSION_SIDE_GATE_RUNTIME_AUDIT_CLEANUP_TEST_ROWS_V1_OK", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
