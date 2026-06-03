#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import os
from decimal import Decimal
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ["DATABASE_URL"]
SYMBOL_DEFAULT = os.environ.get("SYMBOL", "NGN6@RTSX")


def dec(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def table_qty(conn, table: str, symbol: str) -> Decimal:
    # Русский комментарий: разные позиционные таблицы используют разные имена поля количества.
    cols = conn.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = %s
        """,
        (table,),
    ).fetchall()
    names = {r["column_name"] for r in cols}

    for candidate in ("qty", "quantity", "position_qty", "net_qty", "remaining_qty"):
        if candidate in names:
            row = conn.execute(
                f"SELECT COALESCE(SUM({candidate}), 0) AS qty FROM {table} WHERE symbol = %s",
                (symbol,),
            ).fetchone()
            return dec(row["qty"] if row else 0)

    return Decimal("0")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default=SYMBOL_DEFAULT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--max-recent-fill-sec", type=int, default=60)
    args = parser.parse_args()

    if args.dry_run == args.apply:
        raise SystemExit("Укажите ровно один режим: --dry-run или --apply")

    symbol = args.symbol

    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.transaction():
            fills = conn.execute(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN side='BUY' THEN qty ELSE -qty END), 0) AS net_qty,
                    COUNT(*) AS fills_count,
                    MAX(ts) AS last_fill_ts,
                    EXTRACT(EPOCH FROM (now() - MAX(ts))) AS last_fill_age_sec
                FROM fills
                WHERE symbol = %s
                """,
                (symbol,),
            ).fetchone()

            lifecycle = conn.execute(
                """
                SELECT id, symbol, strategy, remaining_qty, entry_price, initial_qty, raw, created_at, updated_at
                FROM position_lifecycle_state
                WHERE symbol = %s
                ORDER BY id
                FOR UPDATE
                """,
                (symbol,),
            ).fetchall()

            positions_qty = dec((conn.execute(
                "SELECT COALESCE(SUM(qty), 0) AS qty FROM positions WHERE symbol = %s",
                (symbol,),
            ).fetchone() or {}).get("qty"))

            # Русский комментарий: position_projection хранит количество внутри JSONB state, а не в колонке qty.
            try:
                projection_row = conn.execute(
                    """
                    SELECT COALESCE(SUM(NULLIF(state->>'qty', '')::numeric), 0) AS qty
                    FROM position_projection
                    WHERE symbol = %s
                    """,
                    (symbol,),
                ).fetchone()
                projection_qty = dec(projection_row["qty"] if projection_row else 0)
            except Exception:
                projection_qty = Decimal("0")

            managed_qty = table_qty(conn, "managed_positions", symbol)

            fills_net_qty = dec(fills["net_qty"])
            lifecycle_qty = sum((dec(r["remaining_qty"]) for r in lifecycle), Decimal("0"))
            last_fill_age_sec = fills["last_fill_age_sec"]
            last_fill_age_sec = float(last_fill_age_sec) if last_fill_age_sec is not None else None

            print("=== NG POSITION RECONCILE FIX V1 ===")
            print(f"mode={'APPLY' if args.apply else 'DRY_RUN'}")
            print(f"symbol={symbol}")
            print(f"fills_net_qty={fills_net_qty}")
            print(f"fills_count={fills['fills_count']}")
            print(f"last_fill_ts={fills['last_fill_ts']}")
            print(f"last_fill_age_sec={last_fill_age_sec}")
            print(f"lifecycle_qty={lifecycle_qty}")
            print(f"lifecycle_rows={len(lifecycle)}")
            print(f"positions_qty={positions_qty}")
            print(f"position_projection_qty={projection_qty}")
            print(f"managed_positions_qty={managed_qty}")

            if positions_qty != 0 or projection_qty != 0 or managed_qty != 0:
                print("verdict=BLOCKED")
                print("reason=active_position_tables_not_empty")
                return 2

            if fills_net_qty == lifecycle_qty:
                print("verdict=NOOP")
                print("reason=already_consistent")
                return 0

            if args.apply and last_fill_age_sec is not None and last_fill_age_sec < args.max_recent_fill_sec:
                print("verdict=BLOCKED")
                print("reason=recent_fill_detected")
                print(f"max_recent_fill_sec={args.max_recent_fill_sec}")
                return 3

            print("planned_action=sync_lifecycle_remaining_qty_to_fills_net_qty")

            if not lifecycle:
                print("planned_insert=1")
                if args.apply:
                    conn.execute(
                        """
                        INSERT INTO position_lifecycle_state (
                            symbol,
                            strategy,
                            remaining_qty,
                            entry_price,
                            initial_qty,
                            trailing_active,
                            current_stop,
                            current_take_profit,
                            raw,
                            created_at,
                            updated_at
                        )
                        VALUES (
                            %s,
                            'default',
                            %s,
                            NULL,
                            %s,
                            false,
                            NULL,
                            NULL,
                            jsonb_build_object(
                                'source', 'ng_position_reconcile_fix_v1',
                                'fills_net_qty', %s::text
                            ),
                            now(),
                            now()
                        )
                        """,
                        (symbol, fills_net_qty, fills_net_qty, str(fills_net_qty)),
                    )
            else:
                keep = lifecycle[0]
                ids_to_delete = [r["id"] for r in lifecycle[1:]]
                print(f"planned_update_id={keep['id']}")
                print(f"planned_delete_extra_rows={ids_to_delete}")

                if args.apply:
                    if ids_to_delete:
                        conn.execute(
                            "DELETE FROM position_lifecycle_state WHERE id = ANY(%s)",
                            (ids_to_delete,),
                        )

                    conn.execute(
                        """
                        UPDATE position_lifecycle_state
                        SET
                            remaining_qty = %s,
                            initial_qty = COALESCE(initial_qty, %s),
                            raw = COALESCE(raw, '{}'::jsonb)
                                  || jsonb_build_object(
                                      'source', 'ng_position_reconcile_fix_v1',
                                      'previous_remaining_qty', %s::text,
                                      'fills_net_qty', %s::text
                                  ),
                            updated_at = now()
                        WHERE id = %s
                        """,
                        (
                            fills_net_qty,
                            fills_net_qty,
                            str(keep["remaining_qty"]),
                            str(fills_net_qty),
                            keep["id"],
                        ),
                    )

            if args.apply:
                print("verdict=APPLIED")
            else:
                print("verdict=DRY_RUN_ONLY")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
