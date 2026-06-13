#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SYMBOL = "GDU6@RTSX"

SQL = """
WITH registry AS (
    SELECT symbol, status, runtime_allowed, execution_enabled, reason, updated_at
    FROM runtime_candidate_registry
    WHERE symbol=%s
),
orders AS (
    SELECT COUNT(*) AS rows
    FROM orders
    WHERE symbol=%s
),
fills AS (
    SELECT COUNT(*) AS rows
    FROM fills
    WHERE symbol=%s
),
positions AS (
    SELECT COUNT(*) AS rows
    FROM positions
    WHERE symbol=%s
)
SELECT
    r.symbol,
    r.status,
    r.runtime_allowed,
    r.execution_enabled,
    r.reason,
    r.updated_at,
    COALESCE(o.rows, 0) AS orders_rows,
    COALESCE(f.rows, 0) AS fills_rows,
    COALESCE(p.rows, 0) AS positions_rows
FROM registry r
LEFT JOIN orders o ON true
LEFT JOIN fills f ON true
LEFT JOIN positions p ON true;
"""

def main() -> int:
    print("=== RUNTIME GOLD WATCH MODE AUDIT V1 ===")
    print("mode=watch_audit")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print()

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (SYMBOL, SYMBOL, SYMBOL, SYMBOL))
            row = cur.fetchone()

    if not row:
        print("AUDIT_VERDICT=FAIL reason=registry_row_missing")
        return 1

    status_ok = row["status"] == "WATCH_RUNTIME_ACTIVE"
    runtime_ok = row["runtime_allowed"] is False
    execution_ok = row["execution_enabled"] is False
    orders_ok = int(row["orders_rows"] or 0) == 0
    fills_ok = int(row["fills_rows"] or 0) == 0
    positions_ok = int(row["positions_rows"] or 0) == 0

    print(
        "AUDIT_ROW "
        f"symbol={row['symbol']} "
        f"status={row['status']} "
        f"runtime_allowed={int(row['runtime_allowed'])} "
        f"execution_enabled={int(row['execution_enabled'])} "
        f"orders_rows={row['orders_rows']} "
        f"fills_rows={row['fills_rows']} "
        f"positions_rows={row['positions_rows']} "
        f"reason={row['reason']} "
        f"updated_at={row['updated_at']}"
    )

    verdict = "PASS" if all([
        status_ok,
        runtime_ok,
        execution_ok,
        orders_ok,
        fills_ok,
        positions_ok,
    ]) else "FAIL"

    print()
    print(f"status_ok={int(status_ok)}")
    print(f"runtime_ok={int(runtime_ok)}")
    print(f"execution_ok={int(execution_ok)}")
    print(f"orders_ok={int(orders_ok)}")
    print(f"fills_ok={int(fills_ok)}")
    print(f"positions_ok={int(positions_ok)}")
    print(f"AUDIT_VERDICT={verdict}")

    if verdict != "PASS":
        return 1

    print("RUNTIME_GOLD_WATCH_MODE_AUDIT_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
