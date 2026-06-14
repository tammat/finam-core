#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from decimal import Decimal

import psycopg2
import psycopg2.extras

RATIO_WARN = Decimal("3")

DDL = """
CREATE TABLE IF NOT EXISTS shadow_runtime_price_scale_audit (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    qty numeric,
    position_avg_price numeric,
    market_price numeric,
    first_fill_price numeric,
    last_fill_price numeric,
    min_fill_price numeric,
    max_fill_price numeric,
    avg_fill_price numeric,
    avg_to_market_ratio numeric,
    fill_to_market_ratio numeric,
    audit_status text NOT NULL,
    audit_reason text NOT NULL,
    runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    raw_json jsonb
);
"""

SQL = """
WITH pos AS (
    SELECT DISTINCT ON (symbol)
        symbol,
        qty,
        avg_price
    FROM shadow_runtime_positions
    ORDER BY symbol, id DESC
),
mtm AS (
    SELECT DISTINCT ON (symbol)
        symbol,
        market_price
    FROM shadow_runtime_mark_to_market
    ORDER BY symbol, id DESC
),
fills AS (
    SELECT
        symbol,
        MIN(fill_price::numeric) AS min_fill_price,
        MAX(fill_price::numeric) AS max_fill_price,
        AVG(fill_price::numeric) AS avg_fill_price,
        (ARRAY_AGG(fill_price::numeric ORDER BY fill_ts ASC, id ASC))[1] AS first_fill_price,
        (ARRAY_AGG(fill_price::numeric ORDER BY fill_ts DESC, id DESC))[1] AS last_fill_price
    FROM shadow_runtime_fills
    GROUP BY symbol
)
SELECT
    p.symbol,
    p.qty,
    p.avg_price AS position_avg_price,
    m.market_price,
    f.first_fill_price,
    f.last_fill_price,
    f.min_fill_price,
    f.max_fill_price,
    f.avg_fill_price
FROM pos p
LEFT JOIN mtm m ON m.symbol=p.symbol
LEFT JOIN fills f ON f.symbol=p.symbol
ORDER BY p.symbol;
"""

def d(v) -> Decimal:
    return Decimal(str(v or 0))

def ratio(a: Decimal, b: Decimal) -> Decimal:
    if a <= 0 or b <= 0:
        return Decimal("0")
    return max(a / b, b / a)

def main() -> int:
    print("=== SHADOW RUNTIME PRICE SCALE AUDIT V1 ===")
    print("mode=price_scale_audit")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    ok = 0
    mismatch = 0
    missing = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(SQL)
            rows = cur.fetchall()

            print("PRICE_SCALE_AUDIT_ROWS")

            for row in rows:
                avg_price = d(row["position_avg_price"])
                market_price = d(row["market_price"])
                avg_fill_price = d(row["avg_fill_price"])

                avg_to_market_ratio = ratio(avg_price, market_price)
                fill_to_market_ratio = ratio(avg_fill_price, market_price)

                if market_price <= 0 or avg_price <= 0 or avg_fill_price <= 0:
                    status = "PRICE_DATA_MISSING"
                    reason = "missing_position_or_market_or_fill_price"
                    missing += 1
                elif avg_to_market_ratio >= RATIO_WARN or fill_to_market_ratio >= RATIO_WARN:
                    status = "SCALE_MISMATCH_CONFIRMED"
                    reason = "position_or_fill_price_far_from_market_price"
                    mismatch += 1
                else:
                    status = "SCALE_OK"
                    reason = "position_fill_and_market_prices_consistent"
                    ok += 1

                payload = {
                    "symbol": row["symbol"],
                    "qty": str(row["qty"]),
                    "position_avg_price": str(row["position_avg_price"]),
                    "market_price": str(row["market_price"]),
                    "first_fill_price": str(row["first_fill_price"]),
                    "last_fill_price": str(row["last_fill_price"]),
                    "min_fill_price": str(row["min_fill_price"]),
                    "max_fill_price": str(row["max_fill_price"]),
                    "avg_fill_price": str(row["avg_fill_price"]),
                    "avg_to_market_ratio": str(avg_to_market_ratio),
                    "fill_to_market_ratio": str(fill_to_market_ratio),
                    "audit_status": status,
                    "audit_reason": reason,
                    "runtime_allowed": False,
                    "execution_enabled": False,
                }

                cur.execute(
                    """
                    INSERT INTO shadow_runtime_price_scale_audit (
                        symbol,
                        qty,
                        position_avg_price,
                        market_price,
                        first_fill_price,
                        last_fill_price,
                        min_fill_price,
                        max_fill_price,
                        avg_fill_price,
                        avg_to_market_ratio,
                        fill_to_market_ratio,
                        audit_status,
                        audit_reason,
                        runtime_allowed,
                        execution_enabled,
                        raw_json
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false,false,%s::jsonb)
                    """,
                    (
                        row["symbol"],
                        row["qty"],
                        row["position_avg_price"],
                        row["market_price"],
                        row["first_fill_price"],
                        row["last_fill_price"],
                        row["min_fill_price"],
                        row["max_fill_price"],
                        row["avg_fill_price"],
                        avg_to_market_ratio,
                        fill_to_market_ratio,
                        status,
                        reason,
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )

                print(
                    "PRICE_SCALE_AUDIT_ROW "
                    f"symbol={row['symbol']} "
                    f"qty={row['qty']} "
                    f"position_avg_price={row['position_avg_price']} "
                    f"market_price={row['market_price']} "
                    f"first_fill_price={row['first_fill_price']} "
                    f"last_fill_price={row['last_fill_price']} "
                    f"min_fill_price={row['min_fill_price']} "
                    f"max_fill_price={row['max_fill_price']} "
                    f"avg_fill_price={row['avg_fill_price']} "
                    f"avg_to_market_ratio={avg_to_market_ratio} "
                    f"fill_to_market_ratio={fill_to_market_ratio} "
                    f"audit_status={status} "
                    f"reason={reason} "
                    "runtime_allowed=0 "
                    "execution_enabled=0"
                )

        conn.commit()

    print()
    print(f"SUMMARY_ROW scale_ok={ok} scale_mismatch={mismatch} price_missing={missing}")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=SHADOW_RUNTIME_PRICE_SCALE_AUDIT_READY")
    print("SHADOW_RUNTIME_PRICE_SCALE_AUDIT_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
