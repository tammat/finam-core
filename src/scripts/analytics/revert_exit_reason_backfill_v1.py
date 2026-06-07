#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import psycopg2
import psycopg2.extras

BACKFILL_SOURCE = "exit_reason_backfill_historical_v1"

FIELDS = [
    "exit_reason",
    "exit_reason_source",
    "exit_trade_id",
    "exit_fill_id",
    "exit_reason_event_ts",
    "exit_reason_join_delta_sec",
]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    mode = "APPLY" if args.apply else "DRY_RUN"

    print("=== EXIT REASON BACKFILL REVERT V1 ===")
    print(f"mode={mode}")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"backfill_source={BACKFILL_SOURCE}")
    print()

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    left(symbol, 2) AS root,
                    count(*) AS rows
                FROM closed_trades
                WHERE payload->>'exit_reason_source' = %s
                GROUP BY 1
                ORDER BY 1
                """,
                (BACKFILL_SOURCE,),
            )
            rows = cur.fetchall()

            print("REVERT_CANDIDATES")
            total = 0
            for r in rows:
                cnt = int(r["rows"] or 0)
                total += cnt
                print(f"CANDIDATE_ROW root={r['root']} rows={cnt}")
            print()

            print("FIELDS_TO_REMOVE")
            for f in FIELDS:
                print(f"FIELD_ROW field={f}")
            print()

            applied = 0
            if args.apply:
                cur.execute(
                    """
                    WITH updated AS (
                        UPDATE closed_trades
                        SET payload =
                            payload
                            - 'exit_reason'
                            - 'exit_reason_source'
                            - 'exit_trade_id'
                            - 'exit_fill_id'
                            - 'exit_reason_event_ts'
                            - 'exit_reason_join_delta_sec'
                        WHERE payload->>'exit_reason_source' = %s
                        RETURNING id
                    )
                    SELECT count(*) AS applied
                    FROM updated
                    """,
                    (BACKFILL_SOURCE,),
                )
                applied = int(cur.fetchone()["applied"] or 0)

    print("SUMMARY")
    print(f"REVERT_CANDIDATES={total}")
    print(f"APPLIED_ROWS={applied}")
    print(f"VERDICT={'APPLIED' if args.apply else 'DRY_RUN_ONLY'}")
    print("EXIT_REASON_BACKFILL_REVERT_V1_OK")


if __name__ == "__main__":
    main()
