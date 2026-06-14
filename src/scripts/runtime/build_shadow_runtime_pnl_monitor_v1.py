#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from decimal import Decimal

import psycopg2
import psycopg2.extras

DDL = """
CREATE TABLE IF NOT EXISTS shadow_runtime_pnl_monitor (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    qty numeric,
    avg_price numeric,
    realized_pnl numeric NOT NULL DEFAULT 0,
    unrealized_pnl numeric NOT NULL DEFAULT 0,
    total_pnl numeric NOT NULL DEFAULT 0,
    equity numeric NOT NULL DEFAULT 0,
    max_equity numeric NOT NULL DEFAULT 0,
    drawdown numeric NOT NULL DEFAULT 0,
    reconciliation_status text,
    runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    raw_json jsonb
);
"""

SQL_POSITIONS = """
SELECT
    p.symbol,
    p.qty,
    p.avg_price,
    p.realized_pnl,
    p.unrealized_pnl,
    r.reconciliation_status
FROM shadow_runtime_positions p
LEFT JOIN (
    SELECT DISTINCT ON (symbol)
        symbol,
        reconciliation_status
    FROM shadow_runtime_position_reconciliation
    ORDER BY symbol, id DESC
) r ON r.symbol=p.symbol
ORDER BY p.symbol;
"""

SQL_PREV_MAX = """
SELECT COALESCE(MAX(max_equity), 0) AS max_equity
FROM shadow_runtime_pnl_monitor
WHERE symbol=%s;
"""

def d(v) -> Decimal:
    return Decimal(str(v or 0))

def main() -> int:
    print("=== SHADOW RUNTIME PNL MONITOR V1 ===")
    print("mode=pnl_monitor")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    rows_written = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(SQL_POSITIONS)
            positions = cur.fetchall()

            print("PNL_ROWS")

            for pos in positions:
                realized = d(pos["realized_pnl"])
                unrealized = d(pos["unrealized_pnl"])
                total_pnl = realized + unrealized
                equity = total_pnl

                cur.execute(SQL_PREV_MAX, (pos["symbol"],))
                prev_max = d(cur.fetchone()["max_equity"])
                max_equity = max(prev_max, equity)
                drawdown = equity - max_equity

                payload = {
                    "symbol": pos["symbol"],
                    "qty": str(pos["qty"]),
                    "avg_price": str(pos["avg_price"]),
                    "realized_pnl": str(realized),
                    "unrealized_pnl": str(unrealized),
                    "total_pnl": str(total_pnl),
                    "equity": str(equity),
                    "max_equity": str(max_equity),
                    "drawdown": str(drawdown),
                    "reconciliation_status": pos["reconciliation_status"],
                    "runtime_allowed": False,
                    "execution_enabled": False,
                }

                cur.execute(
                    """
                    INSERT INTO shadow_runtime_pnl_monitor (
                        symbol,
                        qty,
                        avg_price,
                        realized_pnl,
                        unrealized_pnl,
                        total_pnl,
                        equity,
                        max_equity,
                        drawdown,
                        reconciliation_status,
                        runtime_allowed,
                        execution_enabled,
                        raw_json
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false,false,%s::jsonb);
                    """,
                    (
                        pos["symbol"],
                        pos["qty"],
                        pos["avg_price"],
                        realized,
                        unrealized,
                        total_pnl,
                        equity,
                        max_equity,
                        drawdown,
                        pos["reconciliation_status"],
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )

                rows_written += 1

                print(
                    "PNL_ROW "
                    f"symbol={pos['symbol']} "
                    f"qty={pos['qty']} "
                    f"avg_price={pos['avg_price']} "
                    f"realized_pnl={realized} "
                    f"unrealized_pnl={unrealized} "
                    f"total_pnl={total_pnl} "
                    f"equity={equity} "
                    f"max_equity={max_equity} "
                    f"drawdown={drawdown} "
                    f"reconciliation_status={pos['reconciliation_status']} "
                    "runtime_allowed=0 "
                    "execution_enabled=0"
                )

        conn.commit()

    print()
    print(f"SUMMARY_ROW rows_written={rows_written}")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=SHADOW_RUNTIME_PNL_MONITOR_READY")
    print("SHADOW_RUNTIME_PNL_MONITOR_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
