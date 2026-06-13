#!/usr/bin/env python3
from __future__ import annotations

import json
import os

import psycopg2
import psycopg2.extras

DDL = """
CREATE TABLE IF NOT EXISTS shadow_runtime_candidate_health (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),

    symbol text NOT NULL,
    source text,

    watch_status text,
    route_status text,
    monitor_status text,

    health_status text NOT NULL,
    health_reason text NOT NULL,

    shadow_runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,

    raw_json jsonb
);

CREATE INDEX IF NOT EXISTS idx_shadow_runtime_candidate_health_symbol
ON shadow_runtime_candidate_health(symbol, created_at DESC);
"""

SQL = """
SELECT
    w.symbol,
    w.source,
    w.watch_status,
    COALESCE(r.route_status,'SKIP') AS route_status,
    COALESCE(m.monitor_status,'SKIP') AS monitor_status,
    w.shadow_runtime_allowed,
    w.execution_enabled
FROM (
    SELECT DISTINCT ON (symbol) *
    FROM shadow_runtime_watchlist
    ORDER BY symbol,id DESC
) w
LEFT JOIN (
    SELECT DISTINCT ON (symbol) *
    FROM shadow_runtime_signal_router_sync
    ORDER BY symbol,id DESC
) r
ON r.symbol = w.symbol
LEFT JOIN (
    SELECT DISTINCT ON (symbol) *
    FROM shadow_runtime_signal_monitor
    ORDER BY symbol,id DESC
) m
ON m.symbol = w.symbol
ORDER BY w.symbol;
"""
def main() -> int:

    print("=== SHADOW RUNTIME CANDIDATE HEALTH V1 ===")
    print("mode=candidate_health")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    healthy = 0
    stale = 0
    rejected = 0
    skipped = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(DDL)
            cur.execute(SQL)

            rows = cur.fetchall()

            print("HEALTH_ROWS")

            for row in rows:

                if (
                    row["watch_status"] == "WATCH_SHADOW_RUNTIME"
                    and row["route_status"] == "ROUTE_READY"
                    and row["monitor_status"] == "HEALTHY"
                ):
                    health_status = "HEALTHY_CANDIDATE"
                    reason = "watch_route_monitor_ok"
                    healthy += 1

                elif (
                    row["watch_status"] == "WATCH_SHADOW_RUNTIME"
                    and row["route_status"] == "ROUTE_READY"
                    and row["monitor_status"] == "STALE"
                ):
                    health_status = "STALE_CANDIDATE"
                    reason = "signal_source_stale"
                    stale += 1

                elif row["watch_status"] == "SKIP":
                    health_status = "SKIP"
                    reason = "not_in_shadow_runtime"
                    skipped += 1

                else:
                    health_status = "REJECTED"
                    reason = "candidate_not_ready"
                    rejected += 1

                payload = {
                    "symbol": row["symbol"],
                    "source": row["source"],
                    "watch_status": row["watch_status"],
                    "route_status": row["route_status"],
                    "monitor_status": row["monitor_status"],
                    "health_status": health_status,
                    "health_reason": reason,
                }

                cur.execute(
                    """
                    INSERT INTO shadow_runtime_candidate_health(
                        symbol,
                        source,
                        watch_status,
                        route_status,
                        monitor_status,
                        health_status,
                        health_reason,
                        shadow_runtime_allowed,
                        execution_enabled,
                        raw_json
                    )
                    VALUES(
                        %s,%s,%s,%s,%s,%s,%s,
                        false,
                        false,
                        %s::jsonb
                    )
                    """,
                    (
                        row["symbol"],
                        row["source"],
                        row["watch_status"],
                        row["route_status"],
                        row["monitor_status"],
                        health_status,
                        reason,
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )

                print(
                    "HEALTH_ROW "
                    f"symbol={row['symbol']} "
                    f"watch={row['watch_status']} "
                    f"route={row['route_status']} "
                    f"monitor={row['monitor_status']} "
                    f"health={health_status} "
                    f"runtime_allowed=0 "
                    f"execution_enabled=0"
                )

        conn.commit()

    print()
    print(
        f"SUMMARY_ROW "
        f"healthy_candidates={healthy} "
        f"stale_candidates={stale} "
        f"rejected_candidates={rejected} "
        f"skipped={skipped}"
    )

    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=SHADOW_RUNTIME_CANDIDATE_HEALTH_READY")
    print("SHADOW_RUNTIME_CANDIDATE_HEALTH_V1_OK")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
