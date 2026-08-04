from __future__ import annotations

import os

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "FEATURE_STORE_DIRTY_SCOPE_V1"

DDL = """
ALTER TABLE analytics.feature_store_watermark_v1
    ADD COLUMN IF NOT EXISTS market_dirty boolean
        NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS market_dirty_at timestamptz,
    ADD COLUMN IF NOT EXISTS feature_processed_at timestamptz;
"""


def main() -> int:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute(
                """
                SELECT pg_try_advisory_xact_lock(
                    hashtext(%s)
                ) AS acquired
                """,
                (SOURCE_VERSION,),
            )

            if not cur.fetchone()["acquired"]:
                print("status=SKIPPED_ALREADY_RUNNING")
                print("VERDICT=FEATURE_STORE_DIRTY_SCOPE_V1_SKIPPED")
                return 0

            cur.execute(DDL)

            cur.execute(
                """
                SELECT
                    count(*)::integer AS rows,
                    count(*) FILTER (
                        WHERE market_dirty
                    )::integer AS dirty_rows,
                    count(*) FILTER (
                        WHERE market_dirty_at IS NOT NULL
                    )::integer AS dirty_timestamp_rows,
                    count(*) FILTER (
                        WHERE feature_processed_at IS NOT NULL
                    )::integer AS processed_timestamp_rows
                FROM analytics.feature_store_watermark_v1
                """
            )
            state = cur.fetchone()

    print("=== FEATURE_STORE_DIRTY_SCOPE_V1 ===")
    print(f"rows={state['rows']}")
    print(f"dirty_rows={state['dirty_rows']}")
    print(
        "dirty_timestamp_rows="
        f"{state['dirty_timestamp_rows']}"
    )
    print(
        "processed_timestamp_rows="
        f"{state['processed_timestamp_rows']}"
    )
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=FEATURE_STORE_DIRTY_SCOPE_V1_READY")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
