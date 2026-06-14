#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from decimal import Decimal

import psycopg2
import psycopg2.extras

DDL = """
CREATE TABLE IF NOT EXISTS shadow_runtime_mtm_baseline_reset (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    old_max_equity numeric,
    old_drawdown numeric,
    new_max_equity numeric,
    new_drawdown numeric,
    current_equity numeric,
    baseline_status text NOT NULL,
    baseline_reason text NOT NULL,
    runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    raw_json jsonb
);
"""

SQL = """
WITH latest_ok AS (
    SELECT DISTINCT ON (symbol)
        id,
        symbol,
        equity,
        max_equity,
        drawdown,
        price_scale_status
    FROM shadow_runtime_mark_to_market
    WHERE price_scale_status='SCALE_OK'
    ORDER BY symbol, id DESC
)
SELECT *
FROM latest_ok
ORDER BY symbol;
"""

def d(v) -> Decimal:
    return Decimal(str(v or 0))

def main() -> int:
    print("=== SHADOW RUNTIME MTM BASELINE RESET V1 ===")
    print("mode=mtm_baseline_reset")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    reset = 0
    missing = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(SQL)
            rows = cur.fetchall()

            print("BASELINE_ROWS")

            for row in rows:
                equity = d(row["equity"])
                old_max = d(row["max_equity"])
                old_dd = d(row["drawdown"])

                new_max = equity
                new_dd = Decimal("0")

                status = "BASELINE_RESET"
                reason = "reset_from_latest_scale_ok_mtm"
                reset += 1

                payload = {
                    "symbol": row["symbol"],
                    "old_max_equity": str(old_max),
                    "old_drawdown": str(old_dd),
                    "new_max_equity": str(new_max),
                    "new_drawdown": str(new_dd),
                    "current_equity": str(equity),
                    "source_mtm_id": row["id"],
                    "price_scale_status": row["price_scale_status"],
                    "runtime_allowed": False,
                    "execution_enabled": False,
                }

                cur.execute(
                    """
                    INSERT INTO shadow_runtime_mtm_baseline_reset (
                        symbol,
                        old_max_equity,
                        old_drawdown,
                        new_max_equity,
                        new_drawdown,
                        current_equity,
                        baseline_status,
                        baseline_reason,
                        runtime_allowed,
                        execution_enabled,
                        raw_json
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,false,false,%s::jsonb);
                    """,
                    (
                        row["symbol"],
                        old_max,
                        old_dd,
                        new_max,
                        new_dd,
                        equity,
                        status,
                        reason,
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )

                print(
                    "BASELINE_ROW "
                    f"symbol={row['symbol']} "
                    f"old_max_equity={old_max} "
                    f"old_drawdown={old_dd} "
                    f"new_max_equity={new_max} "
                    f"new_drawdown={new_dd} "
                    f"current_equity={equity} "
                    f"status={status} "
                    f"reason={reason} "
                    "runtime_allowed=0 "
                    "execution_enabled=0"
                )

            if not rows:
                missing = 1
                print("BASELINE_ROW status=NO_SCALE_OK_MTM reason=no_valid_mtm_rows")

        conn.commit()

    print()
    print(f"SUMMARY_ROW reset={reset} missing={missing}")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=SHADOW_RUNTIME_MTM_BASELINE_RESET_READY")
    print("SHADOW_RUNTIME_MTM_BASELINE_RESET_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
