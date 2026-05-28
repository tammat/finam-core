from __future__ import annotations

import argparse
import os

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


CLASSIFY_SQL = """
WITH classified AS (
    SELECT
        id,
        created_at,
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
expired AS (
    SELECT
        id,
        event_class
    FROM classified
    WHERE
        (
            event_class = 'TEST'
            AND created_at < now() - (%(test_days)s::text || ' days')::interval
        )
        OR (
            event_class = 'UNKNOWN'
            AND created_at < now() - (%(unknown_days)s::text || ' days')::interval
        )
        OR (
            event_class = 'PRODUCTION_CANDIDATE'
            AND created_at < now() - (%(production_days)s::text || ' days')::interval
        )
)
SELECT
    event_class,
    count(*) AS expired_rows
FROM expired
GROUP BY event_class
ORDER BY event_class;
"""


DELETE_SQL = """
WITH classified AS (
    SELECT
        id,
        created_at,
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
expired AS (
    SELECT
        id,
        event_class
    FROM classified
    WHERE
        (
            event_class = 'TEST'
            AND created_at < now() - (%(test_days)s::text || ' days')::interval
        )
        OR (
            event_class = 'UNKNOWN'
            AND created_at < now() - (%(unknown_days)s::text || ' days')::interval
        )
        OR (
            event_class = 'PRODUCTION_CANDIDATE'
            AND created_at < now() - (%(production_days)s::text || ' days')::interval
        )
),
deleted AS (
    DELETE FROM risk_event_audit_v1 r
    USING expired e
    WHERE r.id = e.id
    RETURNING e.event_class
)
SELECT
    event_class,
    count(*) AS deleted_rows
FROM deleted
GROUP BY event_class
ORDER BY event_class;
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--apply",
        action="store_true",
        help="Русский комментарий: реально удалить строки. Без флага работает dry-run.",
    )

    parser.add_argument(
        "--production-days",
        type=int,
        default=365,
        help="Русский комментарий: срок хранения production candidate risk events.",
    )

    parser.add_argument(
        "--test-days",
        type=int,
        default=0,
        help="Русский комментарий: срок хранения test rows.",
    )

    parser.add_argument(
        "--unknown-days",
        type=int,
        default=30,
        help="Русский комментарий: срок хранения unknown rows.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    params = {
        "production_days": int(args.production_days),
        "test_days": int(args.test_days),
        "unknown_days": int(args.unknown_days),
    }

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            if args.apply:
                cur.execute(DELETE_SQL, params)
                rows = [dict(r) for r in cur.fetchall()]
                conn.commit()
                mode = "APPLY"
            else:
                cur.execute(CLASSIFY_SQL, params)
                rows = [dict(r) for r in cur.fetchall()]
                conn.rollback()
                mode = "DRY_RUN"

    print("RISK_EVENT_AUDIT_RETENTION_POLICY_V1", flush=True)
    print(
        "RISK_EVENT_AUDIT_RETENTION_POLICY_CONFIG",
        f"mode={mode}",
        f"production_days={args.production_days}",
        f"test_days={args.test_days}",
        f"unknown_days={args.unknown_days}",
        flush=True,
    )

    total = 0
    for r in rows:
        value = int(r.get("expired_rows") or r.get("deleted_rows") or 0)
        total += value

        print(
            "RISK_EVENT_AUDIT_RETENTION_POLICY_ROW",
            f"class={r['event_class']}",
            f"rows={value}",
            flush=True,
        )

    print(
        "RISK_EVENT_AUDIT_RETENTION_POLICY_SUMMARY",
        f"mode={mode}",
        f"rows={total}",
        flush=True,
    )

    print("RISK_EVENT_AUDIT_RETENTION_POLICY_V1_OK", flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
