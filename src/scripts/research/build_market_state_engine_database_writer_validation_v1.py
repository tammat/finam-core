#!/usr/bin/env python3

# ==========================================================
# MARKET_STATE_ENGINE_DATABASE_WRITER_VALIDATION_V1
#
# Проверка корректности записи Market State Snapshot.
#
# Проверяется:
# - snapshot;
# - snapshot values;
# - metadata;
# - идемпотентность;
# - отсутствие дублей;
#
# Runtime и Execution не изменяются.
# ==========================================================

import os
import sys

import psycopg2


def scalar(cur, sql, params=()):
    cur.execute(sql, params)
    row = cur.fetchone()
    return row[0] if row else None


def main():
    print("=== MARKET_STATE_ENGINE_DATABASE_WRITER_VALIDATION_V1 ===")
    print("mode=validation")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("orders_sent=0")

    db = os.environ.get("DATABASE_URL")
    if not db:
        print("db_update=0")
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2

    if db.startswith("sqlite"):
        print("db_update=0")
        print("ERROR=SQLITE_FORBIDDEN")
        return 2

    conn = psycopg2.connect(db)

    with conn:
        with conn.cursor() as cur:

            snapshots = scalar(
                cur,
                """
                SELECT COUNT(*)
                FROM research.market_state_snapshots_v1;
                """,
            )

            values = scalar(
                cur,
                """
                SELECT COUNT(*)
                FROM research.market_state_snapshot_values_v1;
                """,
            )

            metadata = scalar(
                cur,
                """
                SELECT COUNT(*)
                FROM research.market_state_snapshot_metadata_v1;
                """,
            )

            duplicates = scalar(
                cur,
                """
                SELECT COUNT(*)
                FROM (
                    SELECT
                        snapshot_ts,
                        symbol,
                        timeframe,
                        compact_signature,
                        COUNT(*)
                    FROM research.market_state_snapshots_v1
                    GROUP BY
                        snapshot_ts,
                        symbol,
                        timeframe,
                        compact_signature
                    HAVING COUNT(*)>1
                ) q;
                """,
            )

            metadata_missing = scalar(
                cur,
                """
                SELECT COUNT(*)
                FROM research.market_state_snapshots_v1 s
                LEFT JOIN research.market_state_snapshot_metadata_v1 m
                    ON s.snapshot_id=m.snapshot_id
                WHERE m.snapshot_id IS NULL;
                """,
            )

            values_missing = scalar(
                cur,
                """
                SELECT COUNT(*)
                FROM research.market_state_snapshots_v1 s
                LEFT JOIN research.market_state_snapshot_values_v1 v
                    ON s.snapshot_id=v.snapshot_id
                WHERE v.snapshot_id IS NULL;
                """,
            )

    conn.close()

    print()
    print("SUMMARY")
    print(f"snapshots={snapshots}")
    print(f"snapshot_values={values}")
    print(f"metadata={metadata}")
    print(f"duplicates={duplicates}")
    print(f"metadata_missing={metadata_missing}")
    print(f"values_missing={values_missing}")

    verdict = "OK"

    if duplicates:
        verdict = "FAILED_DUPLICATES"

    elif metadata_missing:
        verdict = "FAILED_METADATA"

    elif values_missing:
        verdict = "FAILED_VALUES"

    print()
    print(f"VERDICT={verdict}")

    if verdict != "OK":
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
