#!/usr/bin/env python3
from __future__ import annotations

import json
import os

import psycopg2
import psycopg2.extras

DDL = """
CREATE TABLE IF NOT EXISTS shadow_runtime_readiness_board (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),

    symbol text NOT NULL,
    source text,

    watch_status text,
    route_status text,
    monitor_status text,
    health_status text,

    readiness_status text NOT NULL,
    readiness_reason text NOT NULL,

    shadow_runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,

    raw_json jsonb
);

CREATE INDEX IF NOT EXISTS idx_shadow_runtime_readiness_board_symbol
ON shadow_runtime_readiness_board(symbol, created_at DESC);
"""

SQL = """
SELECT DISTINCT ON (symbol)
    symbol,
    source,
    watch_status,
    route_status,
    monitor_status,
    health_status,
    health_reason,
    shadow_runtime_allowed,
    execution_enabled
FROM shadow_runtime_candidate_health
ORDER BY symbol, id DESC;
"""

def main() -> int:
    print("=== SHADOW RUNTIME READINESS BOARD V1 ===")
    print("mode=readiness_board")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    ready = 0
    stale = 0
    blocked = 0
    review_required = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(SQL)
            rows = cur.fetchall()

            print("READINESS_ROWS")

            for row in rows:
                if (
                    row["health_status"] == "HEALTHY_CANDIDATE"
                    and row["route_status"] == "ROUTE_READY"
                    and row["monitor_status"] == "HEALTHY"
                ):
                    readiness = "READY_FOR_SHADOW_RUNTIME"
                    reason = "candidate_health_route_monitor_ok"
                    ready += 1

                elif row["health_status"] == "STALE_CANDIDATE":
                    readiness = "STALE_NEEDS_REFRESH"
                    reason = "signal_source_stale"
                    stale += 1

                elif row["watch_status"] == "SKIP":
                    readiness = "BLOCKED"
                    reason = "not_in_shadow_runtime_watchlist"
                    blocked += 1

                else:
                    readiness = "REVIEW_REQUIRED"
                    reason = "manual_review_required"
                    review_required += 1

                payload = {
                    "symbol": row["symbol"],
                    "source": row["source"],
                    "watch_status": row["watch_status"],
                    "route_status": row["route_status"],
                    "monitor_status": row["monitor_status"],
                    "health_status": row["health_status"],
                    "health_reason": row["health_reason"],
                    "readiness_status": readiness,
                    "readiness_reason": reason,
                    "shadow_runtime_allowed": False,
                    "execution_enabled": False,
                }

                cur.execute(
                    """
                    INSERT INTO shadow_runtime_readiness_board (
                        symbol,
                        source,
                        watch_status,
                        route_status,
                        monitor_status,
                        health_status,
                        readiness_status,
                        readiness_reason,
                        shadow_runtime_allowed,
                        execution_enabled,
                        raw_json
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,false,false,%s::jsonb)
                    """,
                    (
                        row["symbol"],
                        row["source"],
                        row["watch_status"],
                        row["route_status"],
                        row["monitor_status"],
                        row["health_status"],
                        readiness,
                        reason,
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )

                print(
                    "READINESS_ROW "
                    f"symbol={row['symbol']} "
                    f"watch={row['watch_status']} "
                    f"route={row['route_status']} "
                    f"monitor={row['monitor_status']} "
                    f"health={row['health_status']} "
                    f"readiness={readiness} "
                    f"reason={reason} "
                    "runtime_allowed=0 "
                    "execution_enabled=0"
                )

        conn.commit()

    print()
    print(
        "SUMMARY_ROW "
        f"ready={ready} "
        f"stale={stale} "
        f"blocked={blocked} "
        f"review_required={review_required}"
    )
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=SHADOW_RUNTIME_READINESS_BOARD_READY")
    print("SHADOW_RUNTIME_READINESS_BOARD_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
