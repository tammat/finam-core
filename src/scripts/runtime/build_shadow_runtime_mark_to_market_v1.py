#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from decimal import Decimal

import psycopg2
import psycopg2.extras

PRICE_SCALE_WARN_RATIO = Decimal("3")

DDL = """
CREATE TABLE IF NOT EXISTS shadow_runtime_mark_to_market (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),

    symbol text NOT NULL,

    qty numeric,
    avg_price numeric,

    market_price numeric,
    market_price_ts timestamptz,
    market_price_source text,

    unrealized_pnl numeric,
    total_pnl numeric,
    equity numeric,
    max_equity numeric,
    drawdown numeric,

    price_scale_status text NOT NULL,

    runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,

    raw_json jsonb
);

CREATE INDEX IF NOT EXISTS idx_shadow_runtime_mark_to_market_symbol
ON shadow_runtime_mark_to_market(symbol, created_at DESC);
"""

SQL_POSITIONS = """
SELECT
    symbol,
    qty,
    avg_price,
    realized_pnl,
    unrealized_pnl,
    runtime_allowed,
    execution_enabled
FROM shadow_runtime_positions
ORDER BY symbol;
"""

SQL_PRICE = """
WITH p AS (
    SELECT
        'market_ticks' AS source,
        symbol,
        price::numeric AS price,
        ts
    FROM market_ticks
    WHERE symbol=%s

    UNION ALL

    SELECT
        'market_data' AS source,
        symbol,
        close_price::numeric AS price,
        ts
    FROM market_data
    WHERE symbol=%s

    UNION ALL

    SELECT
        'market_bars' AS source,
        symbol,
        close AS price,
        ts
    FROM market_bars
    WHERE symbol=%s
      AND timeframe='M1'
)
SELECT source, price, ts
FROM p
ORDER BY
    CASE source
        WHEN 'market_ticks' THEN 1
        WHEN 'market_data' THEN 2
        WHEN 'market_bars' THEN 3
        ELSE 9
    END,
    ts DESC
LIMIT 1;
"""

SQL_PREV_MAX = """
SELECT COALESCE(MAX(max_equity), 0) AS max_equity
FROM shadow_runtime_mark_to_market
WHERE symbol=%s;
"""

def d(v) -> Decimal:
    return Decimal(str(v or 0))

def scale_status(avg_price: Decimal, market_price: Decimal) -> str:
    if avg_price <= 0 or market_price <= 0:
        return "PRICE_MISSING_OR_ZERO"

    ratio = max(avg_price / market_price, market_price / avg_price)

    if ratio >= PRICE_SCALE_WARN_RATIO:
        return "SCALE_MISMATCH_SUSPECTED"

    return "SCALE_OK"

def main() -> int:
    print("=== SHADOW RUNTIME MARK TO MARKET V1 ===")
    print("mode=mark_to_market")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    rows_written = 0
    scale_ok = 0
    scale_warn = 0
    price_missing = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(SQL_POSITIONS)
            positions = cur.fetchall()

            print("MTM_ROWS")

            for pos in positions:
                symbol = pos["symbol"]
                qty = d(pos["qty"])
                avg_price = d(pos["avg_price"])

                cur.execute(SQL_PRICE, (symbol, symbol, symbol))
                price_row = cur.fetchone()

                if not price_row:
                    market_price = Decimal("0")
                    market_price_ts = None
                    price_source = None
                    unrealized_pnl = Decimal("0")
                    status = "PRICE_MISSING"
                    price_missing += 1
                else:
                    market_price = d(price_row["price"])
                    market_price_ts = price_row["ts"]
                    price_source = price_row["source"]

                    # Универсальная формула: qty уже со знаком.
                    # Для short qty < 0: если цена ниже avg_price, PnL положительный.
                    unrealized_pnl = qty * (market_price - avg_price)

                    status = scale_status(avg_price, market_price)

                    if status == "SCALE_OK":
                        scale_ok += 1
                    elif status == "SCALE_MISMATCH_SUSPECTED":
                        scale_warn += 1
                    else:
                        price_missing += 1

                total_pnl = d(pos["realized_pnl"]) + unrealized_pnl
                equity = total_pnl

                cur.execute(SQL_PREV_MAX, (symbol,))
                prev_max = d(cur.fetchone()["max_equity"])
                max_equity = max(prev_max, equity)
                drawdown = equity - max_equity

                payload = {
                    "symbol": symbol,
                    "qty": str(qty),
                    "avg_price": str(avg_price),
                    "market_price": str(market_price),
                    "market_price_ts": str(market_price_ts) if market_price_ts else None,
                    "market_price_source": price_source,
                    "unrealized_pnl": str(unrealized_pnl),
                    "total_pnl": str(total_pnl),
                    "equity": str(equity),
                    "max_equity": str(max_equity),
                    "drawdown": str(drawdown),
                    "price_scale_status": status,
                    "runtime_allowed": False,
                    "execution_enabled": False,
                }

                cur.execute(
                    """
                    INSERT INTO shadow_runtime_mark_to_market (
                        symbol,
                        qty,
                        avg_price,
                        market_price,
                        market_price_ts,
                        market_price_source,
                        unrealized_pnl,
                        total_pnl,
                        equity,
                        max_equity,
                        drawdown,
                        price_scale_status,
                        runtime_allowed,
                        execution_enabled,
                        raw_json
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false,false,%s::jsonb);
                    """,
                    (
                        symbol,
                        qty,
                        avg_price,
                        market_price,
                        market_price_ts,
                        price_source,
                        unrealized_pnl,
                        total_pnl,
                        equity,
                        max_equity,
                        drawdown,
                        status,
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )

                rows_written += 1

                print(
                    "MTM_ROW "
                    f"symbol={symbol} "
                    f"qty={qty} "
                    f"avg_price={avg_price} "
                    f"market_price={market_price} "
                    f"market_price_source={price_source} "
                    f"market_price_ts={market_price_ts} "
                    f"unrealized_pnl={unrealized_pnl} "
                    f"total_pnl={total_pnl} "
                    f"equity={equity} "
                    f"max_equity={max_equity} "
                    f"drawdown={drawdown} "
                    f"price_scale_status={status} "
                    "runtime_allowed=0 "
                    "execution_enabled=0"
                )

        conn.commit()

    print()
    print(
        "SUMMARY_ROW "
        f"rows_written={rows_written} "
        f"scale_ok={scale_ok} "
        f"scale_warn={scale_warn} "
        f"price_missing={price_missing}"
    )
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=SHADOW_RUNTIME_MARK_TO_MARKET_READY")
    print("SHADOW_RUNTIME_MARK_TO_MARKET_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
