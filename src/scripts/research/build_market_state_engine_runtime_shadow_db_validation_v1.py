#!/usr/bin/env python3

import os
import psycopg2


def scalar(cur, sql, params=()):
    cur.execute(sql, params)
    row = cur.fetchone()
    return row[0] if row else None


def main() -> int:
    print("=== MARKET_STATE_ENGINE_RUNTIME_SHADOW_DB_VALIDATION_V1 ===")
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
            shadow_snapshots = scalar(
                cur,
                """
                SELECT COUNT(*)
                FROM research.market_state_snapshots_v1
                WHERE source='runtime_shadow_market_state_v1';
                """,
            )

            shadow_values = scalar(
                cur,
                """
                SELECT COUNT(*)
                FROM research.market_state_snapshot_values_v1 v
                JOIN research.market_state_snapshots_v1 s
                  ON s.snapshot_id = v.snapshot_id
                WHERE s.source='runtime_shadow_market_state_v1';
                """,
            )

            shadow_metadata = scalar(
                cur,
                """
                SELECT COUNT(*)
                FROM research.market_state_snapshot_metadata_v1 m
                JOIN research.market_state_snapshots_v1 s
                  ON s.snapshot_id = m.snapshot_id
                WHERE s.source='runtime_shadow_market_state_v1';
                """,
            )

            duplicates = scalar(
                cur,
                """
                SELECT COUNT(*)
                FROM (
                    SELECT snapshot_ts, symbol, timeframe, compact_signature, COUNT(*)
                    FROM research.market_state_snapshots_v1
                    WHERE source='runtime_shadow_market_state_v1'
                    GROUP BY snapshot_ts, symbol, timeframe, compact_signature
                    HAVING COUNT(*) > 1
                ) q;
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

    print("")
    print("SUMMARY")
    print(f"shadow_snapshots={shadow_snapshots}")
    print(f"shadow_values={shadow_values}")
    print(f"shadow_metadata={shadow_metadata}")
    print(f"duplicates={duplicates}")
    print(f"missing_values={missing_values}")
    print(f"missing_metadata={missing_metadata}")

    verdict = "MARKET_STATE_ENGINE_RUNTIME_SHADOW_DB_VALIDATION_OK"
    if not shadow_snapshots:
        verdict = "MARKET_STATE_ENGINE_RUNTIME_SHADOW_DB_VALIDATION_NO_SHADOW_ROWS"
    elif duplicates:
        verdict = "MARKET_STATE_ENGINE_RUNTIME_SHADOW_DB_VALIDATION_DUPLICATES"
    elif missing_values:
        verdict = "MARKET_STATE_ENGINE_RUNTIME_SHADOW_DB_VALIDATION_MISSING_VALUES"
    elif missing_metadata:
        verdict = "MARKET_STATE_ENGINE_RUNTIME_SHADOW_DB_VALIDATION_MISSING_METADATA"

    print(f"VERDICT={verdict}")
    return 0 if verdict == "MARKET_STATE_ENGINE_RUNTIME_SHADOW_DB_VALIDATION_OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
