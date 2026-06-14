#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from decimal import Decimal

import psycopg2
import psycopg2.extras

DDL = """
CREATE TABLE IF NOT EXISTS shadow_runtime_position_reconciliation (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    expected_qty numeric,
    actual_qty numeric,
    qty_diff numeric,
    expected_fills bigint,
    actual_fills_processed bigint,
    fills_diff bigint,
    expected_last_fill_id bigint,
    actual_last_fill_id bigint,
    last_fill_diff bigint,
    reconciliation_status text NOT NULL,
    reconciliation_reason text NOT NULL,
    runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    raw_json jsonb
);
"""

SQL = """
WITH fill_agg AS (
    SELECT
        symbol,
        SUM(
            CASE
                WHEN side='BUY' THEN qty::numeric
                WHEN side='SELL' THEN -qty::numeric
                ELSE 0
            END
        ) AS expected_qty,
        COUNT(*)::bigint AS expected_fills,
        MAX(id)::bigint AS expected_last_fill_id
    FROM shadow_runtime_fills
    GROUP BY symbol
)
SELECT
    f.symbol,
    f.expected_qty,
    f.expected_fills,
    f.expected_last_fill_id,
    p.qty AS actual_qty,
    p.fills_processed AS actual_fills_processed,
    p.last_fill_id AS actual_last_fill_id
FROM fill_agg f
LEFT JOIN shadow_runtime_positions p
    ON p.symbol=f.symbol
ORDER BY f.symbol;
"""

def d(v) -> Decimal:
    return Decimal(str(v or 0))

def main() -> int:
    print("=== SHADOW RUNTIME POSITION RECONCILIATION V1 ===")
    print("mode=position_reconciliation")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    ok = 0
    drift = 0
    missing = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(SQL)
            rows = cur.fetchall()

            print("RECONCILIATION_ROWS")

            for row in rows:
                expected_qty = d(row["expected_qty"])
                actual_qty = d(row["actual_qty"])
                qty_diff = actual_qty - expected_qty

                expected_fills = int(row["expected_fills"] or 0)
                actual_fills = int(row["actual_fills_processed"] or 0)
                fills_diff = actual_fills - expected_fills

                expected_last_fill_id = int(row["expected_last_fill_id"] or 0)
                actual_last_fill_id = int(row["actual_last_fill_id"] or 0)
                last_fill_diff = actual_last_fill_id - expected_last_fill_id

                if row["actual_qty"] is None:
                    status = "MISSING_POSITION"
                    reason = "position_row_missing"
                    missing += 1
                elif qty_diff == 0 and fills_diff == 0 and last_fill_diff == 0:
                    status = "RECONCILED"
                    reason = "position_matches_fills"
                    ok += 1
                else:
                    status = "DRIFT"
                    reason = "position_does_not_match_fills"
                    drift += 1

                payload = {
                    "symbol": row["symbol"],
                    "expected_qty": str(expected_qty),
                    "actual_qty": str(actual_qty),
                    "qty_diff": str(qty_diff),
                    "expected_fills": expected_fills,
                    "actual_fills_processed": actual_fills,
                    "fills_diff": fills_diff,
                    "expected_last_fill_id": expected_last_fill_id,
                    "actual_last_fill_id": actual_last_fill_id,
                    "last_fill_diff": last_fill_diff,
                    "reconciliation_status": status,
                    "reconciliation_reason": reason,
                    "runtime_allowed": False,
                    "execution_enabled": False,
                }

                cur.execute(
                    """
                    INSERT INTO shadow_runtime_position_reconciliation (
                        symbol,
                        expected_qty,
                        actual_qty,
                        qty_diff,
                        expected_fills,
                        actual_fills_processed,
                        fills_diff,
                        expected_last_fill_id,
                        actual_last_fill_id,
                        last_fill_diff,
                        reconciliation_status,
                        reconciliation_reason,
                        runtime_allowed,
                        execution_enabled,
                        raw_json
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false,false,%s::jsonb)
                    """,
                    (
                        row["symbol"],
                        expected_qty,
                        actual_qty,
                        qty_diff,
                        expected_fills,
                        actual_fills,
                        fills_diff,
                        expected_last_fill_id,
                        actual_last_fill_id,
                        last_fill_diff,
                        status,
                        reason,
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )

                print(
                    "RECONCILIATION_ROW "
                    f"symbol={row['symbol']} "
                    f"expected_qty={expected_qty} "
                    f"actual_qty={actual_qty} "
                    f"qty_diff={qty_diff} "
                    f"expected_fills={expected_fills} "
                    f"actual_fills_processed={actual_fills} "
                    f"fills_diff={fills_diff} "
                    f"expected_last_fill_id={expected_last_fill_id} "
                    f"actual_last_fill_id={actual_last_fill_id} "
                    f"last_fill_diff={last_fill_diff} "
                    f"status={status} "
                    f"reason={reason} "
                    "runtime_allowed=0 "
                    "execution_enabled=0"
                )

        conn.commit()

    print()
    print(f"SUMMARY_ROW reconciled={ok} drift={drift} missing={missing}")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=SHADOW_RUNTIME_POSITION_RECONCILIATION_READY")
    print("SHADOW_RUNTIME_POSITION_RECONCILIATION_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
