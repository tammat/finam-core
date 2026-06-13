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
CREATE TABLE IF NOT EXISTS shadow_runtime_signal_router_sync (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    source text,
    watch_status text,
    signal_source_table text,
    route_status text NOT NULL,
    shadow_runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    raw_json jsonb
);
"""

SQL_WATCHLIST = """
SELECT DISTINCT ON (symbol)
    symbol,
    source,
    watch_status,
    shadow_runtime_allowed,
    execution_enabled
FROM shadow_runtime_watchlist
ORDER BY symbol, id DESC;
"""

SQL_TABLE_EXISTS = """
SELECT EXISTS (
    SELECT 1
    FROM information_schema.tables
    WHERE table_schema='public'
      AND table_name=%s
);
"""

def table_exists(cur, table_name: str | None) -> bool:
    if not table_name:
        return False
    cur.execute(SQL_TABLE_EXISTS, (table_name,))
    return bool(cur.fetchone()["exists"])

def main() -> int:
    print("=== SHADOW RUNTIME SIGNAL ROUTER SYNC V1 ===")
    print("mode=router_sync")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    planned = 0
    pending = 0
    skipped = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(SQL_WATCHLIST)
            rows = cur.fetchall()

            print("ROUTER_SYNC_ROWS")

            for row in rows:
                symbol = row["symbol"]
                source_table = SOURCE_TABLES.get(symbol)

                if row["watch_status"] != "WATCH_SHADOW_RUNTIME":
                    route_status = "SKIP"
                    skipped += 1
                elif table_exists(cur, source_table):
                    route_status = "ROUTE_READY"
                    planned += 1
                else:
                    route_status = "SOURCE_PENDING"
                    pending += 1

                payload = {
                    "symbol": symbol,
                    "source": row["source"],
                    "watch_status": row["watch_status"],
                    "signal_source_table": source_table,
                    "route_status": route_status,
                    "shadow_runtime_allowed": bool(row["shadow_runtime_allowed"]),
                    "execution_enabled": False,
                }

                cur.execute(
                    """
                    INSERT INTO shadow_runtime_signal_router_sync (
                        symbol,
                        source,
                        watch_status,
                        signal_source_table,
                        route_status,
                        shadow_runtime_allowed,
                        execution_enabled,
                        raw_json
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,false,%s::jsonb)
                    """,
                    (
                        symbol,
                        row["source"],
                        row["watch_status"],
                        source_table,
                        route_status,
                        bool(row["shadow_runtime_allowed"]),
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )

                print(
                    "ROUTER_SYNC_ROW "
                    f"symbol={symbol} "
                    f"source={row['source']} "
                    f"watch_status={row['watch_status']} "
                    f"signal_source_table={source_table} "
                    f"route_status={route_status} "
                    f"shadow_runtime_allowed={int(bool(row['shadow_runtime_allowed']))} "
                    "execution_enabled=0"
                )

        conn.commit()

    print()
    print(f"SUMMARY_ROW planned={planned} pending={pending} skipped={skipped}")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=SHADOW_RUNTIME_SIGNAL_ROUTER_SYNC_READY")
    print("SHADOW_RUNTIME_SIGNAL_ROUTER_SYNC_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
