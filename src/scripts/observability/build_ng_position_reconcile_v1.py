#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
from decimal import Decimal
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ["DATABASE_URL"]
SYMBOL = os.environ.get("SYMBOL", "NGN6@RTSX")


def d(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def get_one_qty(conn, table: str, column: str = "qty") -> Decimal:
    try:
        row = conn.execute(
            f"SELECT COALESCE(SUM({column}), 0) AS qty FROM {table} WHERE symbol = %s",
            (SYMBOL,),
        ).fetchone()
        return d(row["qty"] if row else 0)
    except Exception:
        return Decimal("0")


def main() -> int:
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        fills_row = conn.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN side='BUY' THEN qty ELSE -qty END), 0) AS net_qty,
                COUNT(*) AS fills,
                MIN(ts) AS first_fill,
                MAX(ts) AS last_fill
            FROM fills
            WHERE symbol = %s
            """,
            (SYMBOL,),
        ).fetchone()

        lifecycle_row = conn.execute(
            """
            SELECT
                COALESCE(SUM(remaining_qty), 0) AS lifecycle_qty,
                COUNT(*) AS rows,
                MIN(created_at) AS first_created,
                MAX(updated_at) AS last_updated
            FROM position_lifecycle_state
            WHERE symbol = %s
            """,
            (SYMBOL,),
        ).fetchone()

        positions_qty = get_one_qty(conn, "positions")

        # Русский комментарий: position_projection хранит количество внутри JSONB state, а не в колонке qty.
        try:
            projection_row = conn.execute(
                """
                SELECT COALESCE(SUM(NULLIF(state->>'qty', '')::numeric), 0) AS qty
                FROM position_projection
                WHERE symbol = %s
                """,
                (SYMBOL,),
            ).fetchone()
            projection_qty = d(projection_row["qty"] if projection_row else 0)
        except Exception:
            projection_qty = Decimal("0")

        managed_qty = get_one_qty(conn, "managed_positions")

    fills_net_qty = d(fills_row["net_qty"])
    lifecycle_qty = d(lifecycle_row["lifecycle_qty"])

    mismatches = []
    if fills_net_qty != lifecycle_qty:
        mismatches.append("FILLS_VS_LIFECYCLE")
    if positions_qty != Decimal("0") and positions_qty != fills_net_qty:
        mismatches.append("FILLS_VS_POSITIONS")
    if projection_qty != Decimal("0") and projection_qty != fills_net_qty:
        mismatches.append("FILLS_VS_PROJECTION")
    if managed_qty != Decimal("0") and managed_qty != fills_net_qty:
        mismatches.append("FILLS_VS_MANAGED")
    if fills_net_qty != Decimal("0") and positions_qty == projection_qty == managed_qty == Decimal("0"):
        mismatches.append("NO_ACTIVE_POSITION_TABLES_BUT_FILLS_NET_NONZERO")

    verdict = "OK" if not mismatches else "MISMATCH"

    print("=== NG POSITION RECONCILE V1 ===")
    print(f"symbol={SYMBOL}")
    print()
    print("FACT")
    print(f"fills_net_qty={fills_net_qty}")
    print(f"fills_count={fills_row['fills']}")
    print(f"first_fill={fills_row['first_fill']}")
    print(f"last_fill={fills_row['last_fill']}")
    print()
    print("POSITION SOURCES")
    print(f"lifecycle_qty={lifecycle_qty}")
    print(f"lifecycle_rows={lifecycle_row['rows']}")
    print(f"lifecycle_first_created={lifecycle_row['first_created']}")
    print(f"lifecycle_last_updated={lifecycle_row['last_updated']}")
    print(f"positions_qty={positions_qty}")
    print(f"position_projection_qty={projection_qty}")
    print(f"managed_positions_qty={managed_qty}")
    print()
    print("VERDICT")
    print(f"status={verdict}")
    print(f"reason={','.join(mismatches) if mismatches else 'consistent'}")

    if verdict != "OK":
        print()
        print("RECOMMENDATION")
        print("1) Не продвигать NG в runtime.")
        print("2) Не считать edge по NG достоверным до reconcile.")
        print("3) Сначала синхронизировать позиционные источники или исключить stale lifecycle из anti-reentry.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
