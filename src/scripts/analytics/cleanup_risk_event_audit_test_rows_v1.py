from __future__ import annotations

import os

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


COUNT_SQL = """
SELECT count(*) AS matched
FROM risk_event_audit_v1
WHERE
    reason IN (
        'daily_loss_limit',
        'wire_audit_storage_test'
    )
    AND symbol = 'BRN6@RTSX'
    AND strategy = 'BR_CONSERVATIVE_BREAKOUT'
    AND timeframe = 'M5'
    AND severity = 'CRITICAL'
    AND raw_json::text ILIKE '%test%';
"""


DELETE_SQL = """
DELETE FROM risk_event_audit_v1
WHERE
    reason IN (
        'daily_loss_limit',
        'wire_audit_storage_test'
    )
    AND symbol = 'BRN6@RTSX'
    AND strategy = 'BR_CONSERVATIVE_BREAKOUT'
    AND timeframe = 'M5'
    AND severity = 'CRITICAL'
    AND raw_json::text ILIKE '%test%'
RETURNING id;
"""


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(COUNT_SQL)
            before = int(cur.fetchone()["matched"])

            cur.execute(DELETE_SQL)
            deleted_ids = [int(r["id"]) for r in cur.fetchall()]

        conn.commit()

    print("RISK_EVENT_AUDIT_CLEANUP_TEST_ROWS_V1", flush=True)
    print(
        "RISK_EVENT_AUDIT_CLEANUP_TEST_ROWS_RESULT",
        f"matched_before={before}",
        f"deleted={len(deleted_ids)}",
        f"deleted_ids={','.join(map(str, deleted_ids)) if deleted_ids else 'none'}",
        flush=True,
    )
    print("RISK_EVENT_AUDIT_CLEANUP_TEST_ROWS_V1_OK", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
