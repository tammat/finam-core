#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import os
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ["DATABASE_URL"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if args.dry_run == args.apply:
        raise SystemExit("Укажите ровно один режим: --dry-run или --apply")

    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        row = conn.execute(
            """
            SELECT
                symbol,
                COALESCE(SUM(CASE WHEN side='BUY' THEN qty ELSE -qty END), 0) AS net_qty,
                COUNT(*) AS fills_count,
                MAX(ts) AS last_fill_ts
            FROM fills
            WHERE symbol = %s
            GROUP BY symbol
            """,
            (args.symbol,),
        ).fetchone()

        if not row:
            print("verdict=NO_FILLS")
            return 0

        state = {
            "symbol": row["symbol"],
            "qty": float(row["net_qty"]),
            "net_qty": float(row["net_qty"]),
            "fills_count": int(row["fills_count"]),
            "last_fill_ts": str(row["last_fill_ts"]),
            "source": "rebuild_position_projection_from_fills_v1",
        }

        print("=== REBUILD POSITION PROJECTION FROM FILLS V1 ===")
        print(f"mode={'APPLY' if args.apply else 'DRY_RUN'}")
        print(f"symbol={row['symbol']}")
        print(f"net_qty={row['net_qty']}")
        print(f"fills_count={row['fills_count']}")
        print(f"last_fill_ts={row['last_fill_ts']}")

        if args.apply:
            conn.execute(
                """
                INSERT INTO position_projection (symbol, state, updated_at)
                VALUES (%s, %s::jsonb, now())
                ON CONFLICT (symbol)
                DO UPDATE SET state = EXCLUDED.state, updated_at = now()
                """,
                (row["symbol"], psycopg.types.json.Jsonb(state)),
            )
            conn.commit()
            print("verdict=APPLIED")
        else:
            print(f"planned_state={state}")
            print("verdict=DRY_RUN_ONLY")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
