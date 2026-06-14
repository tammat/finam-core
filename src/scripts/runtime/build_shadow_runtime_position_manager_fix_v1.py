#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from decimal import Decimal

import psycopg2
import psycopg2.extras

DDL = """
CREATE TABLE IF NOT EXISTS shadow_runtime_positions_fix_audit (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    old_qty numeric,
    old_avg_price numeric,
    new_qty numeric,
    new_avg_price numeric,
    old_realized_pnl numeric,
    new_realized_pnl numeric,
    fills_processed bigint,
    last_fill_id bigint,
    fix_status text NOT NULL,
    runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    raw_json jsonb
);
"""

SQL_SYMBOLS = """
SELECT DISTINCT symbol
FROM shadow_runtime_fills
ORDER BY symbol;
"""

SQL_OLD_POSITION = """
SELECT *
FROM shadow_runtime_positions
WHERE symbol=%s;
"""

SQL_FILLS = """
SELECT
    id,
    symbol,
    side,
    qty::numeric AS qty,
    fill_price::numeric AS fill_price
FROM shadow_runtime_fills
WHERE symbol=%s
ORDER BY id;
"""

SQL_UPDATE_POSITION = """
INSERT INTO shadow_runtime_positions (
    symbol,
    qty,
    avg_price,
    fills_processed,
    last_fill_id,
    realized_pnl,
    unrealized_pnl,
    paper_only,
    runtime_allowed,
    execution_enabled,
    raw_json,
    updated_at
)
VALUES (
    %(symbol)s,
    %(qty)s,
    %(avg_price)s,
    %(fills_processed)s,
    %(last_fill_id)s,
    %(realized_pnl)s,
    0,
    true,
    false,
    false,
    %(raw_json)s,
    now()
)
ON CONFLICT (symbol) DO UPDATE
SET
    qty=EXCLUDED.qty,
    avg_price=EXCLUDED.avg_price,
    fills_processed=EXCLUDED.fills_processed,
    last_fill_id=EXCLUDED.last_fill_id,
    realized_pnl=EXCLUDED.realized_pnl,
    unrealized_pnl=0,
    raw_json=EXCLUDED.raw_json,
    updated_at=now();
"""

def dec(v) -> Decimal:
    return Decimal(str(v or 0))

def same_direction(qty: Decimal, incoming: Decimal) -> bool:
    return (qty > 0 and incoming > 0) or (qty < 0 and incoming < 0)

def process_fill(qty: Decimal, avg_price: Decimal | None, realized: Decimal, incoming: Decimal, price: Decimal):
    if incoming == 0:
        return qty, avg_price, realized

    if qty == 0:
        return incoming, price, realized

    if same_direction(qty, incoming):
        new_qty = qty + incoming
        new_avg = ((abs(qty) * dec(avg_price)) + (abs(incoming) * price)) / abs(new_qty)
        return new_qty, new_avg, realized

    close_qty = min(abs(qty), abs(incoming))

    if qty > 0:
        realized += close_qty * (price - dec(avg_price))
    else:
        realized += close_qty * (dec(avg_price) - price)

    new_qty = qty + incoming

    if new_qty == 0:
        return Decimal("0"), None, realized

    if abs(incoming) > abs(qty):
        return new_qty, price, realized

    return new_qty, avg_price, realized

def main() -> int:
    print("=== SHADOW RUNTIME POSITION MANAGER FIX V1 ===")
    print("mode=position_manager_fix")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    fixed = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(SQL_SYMBOLS)
            symbols = [r["symbol"] for r in cur.fetchall()]

            print("FIX_ROWS")

            for symbol in symbols:
                cur.execute(SQL_OLD_POSITION, (symbol,))
                old = cur.fetchone()

                old_qty = dec(old["qty"]) if old else Decimal("0")
                old_avg = dec(old["avg_price"]) if old and old["avg_price"] is not None else None
                old_realized = dec(old["realized_pnl"]) if old else Decimal("0")

                cur.execute(SQL_FILLS, (symbol,))
                fills = cur.fetchall()

                qty = Decimal("0")
                avg_price: Decimal | None = None
                realized = Decimal("0")
                last_fill_id = 0

                for fill in fills:
                    fill_qty = dec(fill["qty"])
                    price = dec(fill["fill_price"])
                    incoming = fill_qty if fill["side"] == "BUY" else -fill_qty

                    qty, avg_price, realized = process_fill(qty, avg_price, realized, incoming, price)
                    last_fill_id = int(fill["id"])

                payload = {
                    "symbol": symbol,
                    "old_qty": str(old_qty),
                    "old_avg_price": str(old_avg) if old_avg is not None else None,
                    "new_qty": str(qty),
                    "new_avg_price": str(avg_price) if avg_price is not None else None,
                    "old_realized_pnl": str(old_realized),
                    "new_realized_pnl": str(realized),
                    "fills_processed": len(fills),
                    "last_fill_id": last_fill_id,
                    "runtime_allowed": False,
                    "execution_enabled": False,
                    "fix": "recomputed_from_fills_with_close_and_reversal_accounting",
                }

                cur.execute(
                    SQL_UPDATE_POSITION,
                    {
                        "symbol": symbol,
                        "qty": qty,
                        "avg_price": avg_price,
                        "fills_processed": len(fills),
                        "last_fill_id": last_fill_id,
                        "realized_pnl": realized,
                        "raw_json": json.dumps(payload, ensure_ascii=False),
                    },
                )

                cur.execute(
                    """
                    INSERT INTO shadow_runtime_positions_fix_audit (
                        symbol,
                        old_qty,
                        old_avg_price,
                        new_qty,
                        new_avg_price,
                        old_realized_pnl,
                        new_realized_pnl,
                        fills_processed,
                        last_fill_id,
                        fix_status,
                        runtime_allowed,
                        execution_enabled,
                        raw_json
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false,false,%s::jsonb);
                    """,
                    (
                        symbol,
                        old_qty,
                        old_avg,
                        qty,
                        avg_price,
                        old_realized,
                        realized,
                        len(fills),
                        last_fill_id,
                        "FIX_APPLIED",
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )

                fixed += 1

                print(
                    "FIX_ROW "
                    f"symbol={symbol} "
                    f"old_qty={old_qty} "
                    f"old_avg_price={old_avg} "
                    f"new_qty={qty} "
                    f"new_avg_price={avg_price} "
                    f"old_realized_pnl={old_realized} "
                    f"new_realized_pnl={realized} "
                    f"fills_processed={len(fills)} "
                    f"last_fill_id={last_fill_id} "
                    "fix_status=FIX_APPLIED "
                    "runtime_allowed=0 "
                    "execution_enabled=0"
                )

        conn.commit()

    print()
    print(f"SUMMARY_ROW fixed={fixed}")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=SHADOW_RUNTIME_POSITION_MANAGER_FIX_READY")
    print("SHADOW_RUNTIME_POSITION_MANAGER_FIX_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
