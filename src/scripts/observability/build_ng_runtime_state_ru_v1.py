#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import psycopg

DATABASE_URL = os.environ["DATABASE_URL"]
SYMBOL = os.environ.get("SYMBOL", "NGN6@RTSX")


def print_rows(title: str, rows) -> None:
    print()
    print(title)
    if not rows:
        print("нет данных")
        return
    for row in rows:
        print(dict(row))


def main() -> int:
    with psycopg.connect(DATABASE_URL, row_factory=psycopg.rows.dict_row) as conn:
        fills = conn.execute(
            """
            SELECT symbol, side, qty, price, ts, ts AT TIME ZONE 'Europe/Moscow' AS ts_msk
            FROM fills
            WHERE symbol = %s
            ORDER BY ts DESC
            LIMIT 20
            """,
            (SYMBOL,),
        ).fetchall()

        positions = conn.execute(
            """
            SELECT *
            FROM positions
            WHERE symbol = %s
            """,
            (SYMBOL,),
        ).fetchall()

        projection = conn.execute(
            """
            SELECT *
            FROM position_projection
            WHERE symbol = %s
            """,
            (SYMBOL,),
        ).fetchall()

        managed = conn.execute(
            """
            SELECT *
            FROM managed_positions
            WHERE symbol = %s
            """,
            (SYMBOL,),
        ).fetchall()

        lifecycle = conn.execute(
            """
            SELECT *
            FROM position_lifecycle_state
            WHERE symbol = %s
            """,
            (SYMBOL,),
        ).fetchall()

    print("=== NG RUNTIME STATE RU V1 ===")
    print(f"symbol={SYMBOL}")

    print_rows("ПОСЛЕДНИЕ FILLS", fills)
    print_rows("POSITIONS", positions)
    print_rows("POSITION_PROJECTION", projection)
    print_rows("MANAGED_POSITIONS", managed)
    print_rows("POSITION_LIFECYCLE_STATE", lifecycle)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
