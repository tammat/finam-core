#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from decimal import Decimal

import psycopg2
import psycopg2.extras

DDL = """
CREATE TABLE IF NOT EXISTS shadow_runtime_positions (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL UNIQUE,
    qty numeric NOT NULL DEFAULT 0,
    avg_price numeric,
    fills_processed bigint NOT NULL DEFAULT 0,
    last_fill_id bigint,
    realized_pnl numeric NOT NULL DEFAULT 0,
    unrealized_pnl numeric NOT NULL DEFAULT 0,
    paper_only boolean NOT NULL DEFAULT true,
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

SQL_POSITION = """
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
  AND id > %s
ORDER BY id;
"""

SQL_UPSERT = """
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
    0,
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
    raw_json=EXCLUDED.raw_json,
    updated_at=now();
"""

def d(value) -> Decimal:
    return Decimal(str(value or 0))

def main() -> int:
    print("=== SHADOW RUNTIME POSITION MANAGER V1 ===")
    print("mode=position_manager")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    symbols_processed = 0
    fills_processed_total = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(SQL_SYMBOLS)
            symbols = [r["symbol"] for r in cur.fetchall()]

            print("POSITION_ROWS")

            for symbol in symbols:
                cur.execute(SQL_POSITION, (symbol,))
                pos = cur.fetchone()

                old_qty = d(pos["qty"]) if pos else Decimal("0")
                old_avg = d(pos["avg_price"]) if pos and pos["avg_price"] is not None else None
                old_processed = int(pos["fills_processed"]) if pos else 0
                last_fill_id = int(pos["last_fill_id"]) if pos and pos["last_fill_id"] else 0

                cur.execute(SQL_FILLS, (symbol, last_fill_id))
                fills = cur.fetchall()

                qty = old_qty
                avg_price = old_avg
                processed = old_processed
                latest_fill_id = last_fill_id

                for fill in fills:
                    fill_qty = d(fill["qty"])
                    fill_price = d(fill["fill_price"])
                    signed_qty = fill_qty if fill["side"] == "BUY" else -fill_qty

                    if qty == 0:
                        qty = signed_qty
                        avg_price = fill_price
                    else:
                        new_qty = qty + signed_qty
                        if new_qty != 0:
                            avg_price = ((abs(qty) * d(avg_price)) + (abs(signed_qty) * fill_price)) / abs(new_qty)
                        qty = new_qty

                    processed += 1
                    latest_fill_id = int(fill["id"])

                payload = {
                    "symbol": symbol,
                    "qty": str(qty),
                    "avg_price": str(avg_price) if avg_price is not None else None,
                    "fills_processed": processed,
                    "last_fill_id": latest_fill_id,
                    "new_fills_processed": len(fills),
                    "paper_only": True,
                    "runtime_allowed": False,
                    "execution_enabled": False,
                }

                cur.execute(
                    SQL_UPSERT,
                    {
                        "symbol": symbol,
                        "qty": qty,
                        "avg_price": avg_price,
                        "fills_processed": processed,
                        "last_fill_id": latest_fill_id,
                        "raw_json": json.dumps(payload, ensure_ascii=False),
                    },
                )

                symbols_processed += 1
                fills_processed_total += len(fills)

                status = "ACTIVE" if processed > 0 else "NO_POSITION"

                print(
                    "POSITION_ROW "
                    f"symbol={symbol} "
                    f"new_fills={len(fills)} "
                    f"fills_processed={processed} "
                    f"last_fill_id={latest_fill_id} "
                    f"qty={qty} "
                    f"avg_price={avg_price} "
                    f"status={status} "
                    "runtime_allowed=0 "
                    "execution_enabled=0"
                )

        conn.commit()

    print()
    print(f"SUMMARY_ROW symbols={symbols_processed} new_fills_processed={fills_processed_total}")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=SHADOW_RUNTIME_POSITION_MANAGER_READY")
    print("SHADOW_RUNTIME_POSITION_MANAGER_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
