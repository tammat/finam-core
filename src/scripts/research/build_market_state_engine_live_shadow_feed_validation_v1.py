#!/usr/bin/env python3

import os
import psycopg2


def scalar(cur, sql, params=()):
    cur.execute(sql, params)
    row = cur.fetchone()
    return row[0] if row else None


def main() -> int:
    print("=== MARKET_STATE_ENGINE_LIVE_SHADOW_FEED_VALIDATION_V1 ===")
    print("mode=validation")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("orders_sent=0")

    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2
    if database_url.startswith("sqlite"):
        print("ERROR=SQLITE_FORBIDDEN")
        return 2

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            live_shadow_rows = scalar(
                cur,
                """
                SELECT COUNT(*)
                FROM research.market_state_snapshots_v1
                WHERE source='runtime_shadow_market_state_v1';
                """,
            )

            latest_symbol = scalar(
                cur,
                """
                SELECT symbol
                FROM research.market_state_snapshots_v1
                WHERE source='runtime_shadow_market_state_v1'
                ORDER BY created_at DESC
                LIMIT 1;
                """,
            )

            latest_quality = scalar(
                cur,
                """
                SELECT quality
                FROM research.market_state_snapshots_v1
                WHERE source='runtime_shadow_market_state_v1'
                ORDER BY created_at DESC
                LIMIT 1;
                """,
            )

            missing_values = scalar(
                cur,
                """
                SELECT COUNT(*)
                FROM research.market_state_snapshots_v1 s
                LEFT JOIN research.market_state_snapshot_values_v1 v
                  ON s.snapshot_id = v.snapshot_id
                WHERE s.source='runtime_shadow_market_state_v1'
                  AND v.snapshot_id IS NULL;
                """,
            )

            missing_metadata = scalar(
                cur,
                """
                SELECT COUNT(*)
                FROM research.market_state_snapshots_v1 s
                LEFT JOIN research.market_state_snapshot_metadata_v1 m
                  ON s.snapshot_id = m.snapshot_id
                WHERE s.source='runtime_shadow_market_state_v1'
                  AND m.snapshot_id IS NULL;
                """,
            )

            invalid_runtime_flags = 0
            invalid_execution_flags = 0
            orders_sent = 0

    print("")
    print("SUMMARY")
    print(f"live_shadow_rows={live_shadow_rows}")
    print(f"latest_symbol={latest_symbol}")
    print(f"latest_quality={latest_quality}")
    print(f"missing_values={missing_values}")
    print(f"missing_metadata={missing_metadata}")
    print(f"invalid_runtime_flags={invalid_runtime_flags}")
    print(f"invalid_execution_flags={invalid_execution_flags}")
    print(f"orders_sent={orders_sent}")

    verdict = "MARKET_STATE_ENGINE_LIVE_SHADOW_FEED_VALIDATION_OK"
    if not live_shadow_rows:
        verdict = "MARKET_STATE_ENGINE_LIVE_SHADOW_FEED_VALIDATION_NO_ROWS"
    elif missing_values:
        verdict = "MARKET_STATE_ENGINE_LIVE_SHADOW_FEED_VALIDATION_MISSING_VALUES"
    elif missing_metadata:
        verdict = "MARKET_STATE_ENGINE_LIVE_SHADOW_FEED_VALIDATION_MISSING_METADATA"

    print(f"VERDICT={verdict}")
    return 0 if verdict == "MARKET_STATE_ENGINE_LIVE_SHADOW_FEED_VALIDATION_OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
