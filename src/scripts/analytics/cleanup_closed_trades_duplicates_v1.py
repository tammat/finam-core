#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import psycopg2

SOURCE = "closed_trade_engine_v1_1"

parser = argparse.ArgumentParser()
parser.add_argument("--apply", action="store_true")
args = parser.parse_args()

mode = "APPLY" if args.apply else "DRY_RUN"

print("=== CLOSED TRADES DUPLICATE CLEANUP V1 ===")
print(f"mode={mode}")
print(f"source={SOURCE}")

conn = psycopg2.connect(os.environ["DATABASE_URL"])

with conn:
    with conn.cursor() as cur:
        cur.execute("""
            WITH ranked AS (
                SELECT
                    id,
                    row_number() OVER (
                        PARTITION BY
                            symbol, side, entry_ts, exit_ts,
                            entry_price, exit_price, qty, source
                        ORDER BY id
                    ) AS rn
                FROM closed_trades
                WHERE source = %s
                  AND left(symbol, 2) IN ('BR','NG')
            )
            SELECT count(*)
            FROM ranked
            WHERE rn > 1
        """, (SOURCE,))
        duplicates = cur.fetchone()[0]

        print(f"DUPLICATE_ROWS_TO_DELETE={duplicates}")

        if args.apply:
            cur.execute("""
                WITH ranked AS (
                    SELECT
                        id,
                        row_number() OVER (
                            PARTITION BY
                                symbol, side, entry_ts, exit_ts,
                                entry_price, exit_price, qty, source
                            ORDER BY id
                        ) AS rn
                    FROM closed_trades
                    WHERE source = %s
                      AND left(symbol, 2) IN ('BR','NG')
                ),
                deleted AS (
                    DELETE FROM closed_trades ct
                    USING ranked r
                    WHERE ct.id = r.id
                      AND r.rn > 1
                    RETURNING ct.id
                )
                SELECT count(*)
                FROM deleted
            """, (SOURCE,))
            deleted = cur.fetchone()[0]
            print(f"DELETED_ROWS={deleted}")
            print("VERDICT=APPLIED")
        else:
            print("DELETED_ROWS=0")
            print("VERDICT=DRY_RUN")

print("CLOSED_TRADES_DUPLICATE_CLEANUP_V1_OK")
