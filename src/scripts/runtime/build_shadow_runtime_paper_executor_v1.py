#!/usr/bin/env python3
from __future__ import annotations

import json
import os

import psycopg2
import psycopg2.extras

SOURCE_TABLES = {
    "LKOH@MISX": "lkoh_shadow_signals",
    "GDU6@RTSX": "runtime_shadow_gold_signals",
}

DDL = """
CREATE TABLE IF NOT EXISTS shadow_runtime_orders (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    strategy text,
    signal_ts timestamptz,
    side text,
    qty numeric,
    paper_only boolean NOT NULL DEFAULT true,
    runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    raw_json jsonb
);

CREATE TABLE IF NOT EXISTS shadow_runtime_fills (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    strategy text,
    order_id bigint,
    fill_ts timestamptz,
    side text,
    qty numeric,
    fill_price numeric,
    paper_only boolean NOT NULL DEFAULT true,
    runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    raw_json jsonb
);

CREATE INDEX IF NOT EXISTS idx_shadow_runtime_orders_symbol_ts
ON shadow_runtime_orders(symbol, signal_ts DESC);

CREATE INDEX IF NOT EXISTS idx_shadow_runtime_fills_symbol_ts
ON shadow_runtime_fills(symbol, fill_ts DESC);
"""

SQL_READINESS = """
SELECT DISTINCT ON (symbol)
    symbol,
    source,
    readiness_status,
    readiness_reason
FROM shadow_runtime_readiness_board
ORDER BY symbol, id DESC;
"""

def table_exists(cur, table_name: str | None) -> bool:
    if not table_name:
        return False
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema='public'
              AND table_name=%s
        );
        """,
        (table_name,),
    )
    return bool(cur.fetchone()["exists"])

def fetch_signals(cur, table_name: str, symbol: str) -> list[dict]:
    cur.execute(
        f"""
        SELECT
            symbol,
            strategy,
            signal_ts,
            side,
            entry_price
        FROM {table_name}
        WHERE symbol=%s
        ORDER BY signal_ts;
        """,
        (symbol,),
    )
    return [dict(r) for r in cur.fetchall()]

def main() -> int:
    print("=== SHADOW RUNTIME PAPER EXECUTOR V1 ===")
    print("mode=paper_executor")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    active = 0
    stale = 0
    blocked = 0
    orders_written = 0
    fills_written = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(SQL_READINESS)
            rows = cur.fetchall()

            print("EXECUTOR_ROWS")

            for row in rows:
                symbol = row["symbol"]
                source_table = SOURCE_TABLES.get(symbol)

                if row["readiness_status"] != "READY_FOR_SHADOW_RUNTIME":
                    if row["readiness_status"] == "STALE_NEEDS_REFRESH":
                        status = "SKIP_STALE_SOURCE"
                        stale += 1
                    else:
                        status = "BLOCKED"
                        blocked += 1

                    print(
                        "EXECUTOR_ROW "
                        f"symbol={symbol} "
                        f"readiness={row['readiness_status']} "
                        f"source_table={source_table} "
                        "signals_seen=0 "
                        "paper_orders=0 "
                        "paper_fills=0 "
                        f"status={status} "
                        "runtime_allowed=0 "
                        "execution_enabled=0"
                    )
                    continue

                if not table_exists(cur, source_table):
                    status = "SOURCE_MISSING"
                    blocked += 1
                    signals = []
                else:
                    signals = fetch_signals(cur, source_table, symbol)
                    status = "ACTIVE" if signals else "NO_SIGNALS"
                    if signals:
                        active += 1
                    else:
                        blocked += 1

                symbol_orders = 0
                symbol_fills = 0

                for sig in signals:
                    qty = 1

                    payload_order = {
                        "symbol": sig["symbol"],
                        "strategy": sig.get("strategy"),
                        "signal_ts": str(sig["signal_ts"]),
                        "side": sig["side"],
                        "qty": qty,
                        "paper_only": True,
                        "runtime_allowed": False,
                        "execution_enabled": False,
                        "source_table": source_table,
                    }

                    cur.execute(
                        """
                        INSERT INTO shadow_runtime_orders (
                            symbol,
                            strategy,
                            signal_ts,
                            side,
                            qty,
                            paper_only,
                            runtime_allowed,
                            execution_enabled,
                            raw_json
                        )
                        VALUES (%s,%s,%s,%s,%s,true,false,false,%s::jsonb)
                        RETURNING id;
                        """,
                        (
                            sig["symbol"],
                            sig.get("strategy"),
                            sig["signal_ts"],
                            sig["side"],
                            qty,
                            json.dumps(payload_order, ensure_ascii=False, default=str),
                        ),
                    )
                    order_id = cur.fetchone()["id"]
                    symbol_orders += 1
                    orders_written += 1

                    payload_fill = {
                        "symbol": sig["symbol"],
                        "strategy": sig.get("strategy"),
                        "order_id": order_id,
                        "fill_ts": str(sig["signal_ts"]),
                        "side": sig["side"],
                        "qty": qty,
                        "fill_price": sig.get("entry_price"),
                        "paper_only": True,
                        "runtime_allowed": False,
                        "execution_enabled": False,
                        "source_table": source_table,
                    }

                    cur.execute(
                        """
                        INSERT INTO shadow_runtime_fills (
                            symbol,
                            strategy,
                            order_id,
                            fill_ts,
                            side,
                            qty,
                            fill_price,
                            paper_only,
                            runtime_allowed,
                            execution_enabled,
                            raw_json
                        )
                        VALUES (%s,%s,%s,%s,%s,%s,%s,true,false,false,%s::jsonb);
                        """,
                        (
                            sig["symbol"],
                            sig.get("strategy"),
                            order_id,
                            sig["signal_ts"],
                            sig["side"],
                            qty,
                            sig.get("entry_price"),
                            json.dumps(payload_fill, ensure_ascii=False, default=str),
                        ),
                    )
                    symbol_fills += 1
                    fills_written += 1

                print(
                    "EXECUTOR_ROW "
                    f"symbol={symbol} "
                    f"readiness={row['readiness_status']} "
                    f"source_table={source_table} "
                    f"signals_seen={len(signals)} "
                    f"paper_orders={symbol_orders} "
                    f"paper_fills={symbol_fills} "
                    f"status={status} "
                    "runtime_allowed=0 "
                    "execution_enabled=0"
                )

        conn.commit()

    print()
    print(
        "SUMMARY_ROW "
        f"active={active} "
        f"stale={stale} "
        f"blocked={blocked} "
        f"orders_written={orders_written} "
        f"fills_written={fills_written}"
    )
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=SHADOW_RUNTIME_PAPER_EXECUTOR_READY")
    print("SHADOW_RUNTIME_PAPER_EXECUTOR_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
