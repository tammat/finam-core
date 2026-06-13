#!/usr/bin/env python3
from __future__ import annotations

import json
import os

import psycopg2
import psycopg2.extras

DDL = """
CREATE TABLE IF NOT EXISTS shadow_runtime_watchlist (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    source text,
    watch_status text NOT NULL,
    shadow_runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    raw_json jsonb
);

CREATE INDEX IF NOT EXISTS idx_shadow_runtime_watchlist_symbol
ON shadow_runtime_watchlist(symbol, created_at DESC);
"""

SQL = """
SELECT DISTINCT ON (symbol)
    symbol,
    source,
    enable_status,
    shadow_runtime_allowed,
    execution_enabled
FROM shadow_runtime_enable_package
ORDER BY symbol, id DESC;
"""

def main() -> int:
    print("=== SHADOW RUNTIME WATCHLIST V1 ===")
    print("mode=watchlist")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    watch = 0
    skipped = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(SQL)
            rows = cur.fetchall()

            print("WATCHLIST_ROWS")

            for row in rows:
                if row["enable_status"] == "SHADOW_RUNTIME_ENABLED" and row["shadow_runtime_allowed"]:
                    watch_status = "WATCH_SHADOW_RUNTIME"
                    watch += 1
                else:
                    watch_status = "SKIP"
                    skipped += 1

                payload = {
                    "symbol": row["symbol"],
                    "source": row["source"],
                    "enable_status": row["enable_status"],
                    "watch_status": watch_status,
                    "shadow_runtime_allowed": bool(row["shadow_runtime_allowed"]),
                    "execution_enabled": False,
                }

                cur.execute(
                    """
                    INSERT INTO shadow_runtime_watchlist (
                        symbol,
                        source,
                        watch_status,
                        shadow_runtime_allowed,
                        execution_enabled,
                        raw_json
                    )
                    VALUES (%s,%s,%s,%s,false,%s::jsonb)
                    """,
                    (
                        row["symbol"],
                        row["source"],
                        watch_status,
                        bool(row["shadow_runtime_allowed"]),
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )

                print(
                    "WATCHLIST_ROW "
                    f"symbol={row['symbol']} "
                    f"source={row['source']} "
                    f"watch_status={watch_status} "
                    f"shadow_runtime_allowed={int(bool(row['shadow_runtime_allowed']))} "
                    "execution_enabled=0"
                )

        conn.commit()

    print()
    print(f"SUMMARY_ROW watch={watch} skipped={skipped}")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=SHADOW_RUNTIME_WATCHLIST_READY")
    print("SHADOW_RUNTIME_WATCHLIST_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
