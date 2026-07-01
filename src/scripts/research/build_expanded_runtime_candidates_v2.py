from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics_global_edge_expanded_runtime_candidates_v2 (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    symbol TEXT NOT NULL,
                    asset_class TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    strategy_family TEXT NOT NULL,
                    regime TEXT NOT NULL,
                    walk_forward_status TEXT NOT NULL,
                    candidate_status TEXT NOT NULL,
                    runtime_allowed BOOLEAN NOT NULL DEFAULT false,
                    execution_allowed BOOLEAN NOT NULL DEFAULT false,
                    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,
                    UNIQUE(symbol, timeframe, strategy_family, regime)
                );
            """)

            cur.execute("""
                SELECT symbol, asset_class, timeframe, strategy_family, regime, walk_forward_status
                FROM analytics_global_edge_expanded_walk_forward_v2
                ORDER BY symbol, timeframe, strategy_family, regime;
            """)
            rows = cur.fetchall()

            saved = 0

            for symbol, asset_class, timeframe, strategy_family, regime, wf_status in rows:
                candidate_status = (
                    "RESEARCH_CANDIDATE"
                    if wf_status == "WALK_FORWARD_PASS"
                    else "RESEARCH_REJECTED"
                )

                cur.execute("""
                    INSERT INTO analytics_global_edge_expanded_runtime_candidates_v2
                    (
                        symbol,
                        asset_class,
                        timeframe,
                        strategy_family,
                        regime,
                        walk_forward_status,
                        candidate_status,
                        runtime_allowed,
                        execution_allowed,
                        micro_live_allowed
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,false,false,false)
                    ON CONFLICT (symbol, timeframe, strategy_family, regime)
                    DO UPDATE SET
                        created_at = now(),
                        asset_class = EXCLUDED.asset_class,
                        walk_forward_status = EXCLUDED.walk_forward_status,
                        candidate_status = EXCLUDED.candidate_status,
                        runtime_allowed = false,
                        execution_allowed = false,
                        micro_live_allowed = false;
                """, (
                    symbol,
                    asset_class,
                    timeframe,
                    strategy_family,
                    regime,
                    wf_status,
                    candidate_status,
                ))
                saved += 1

    print("=== EXPANDED_RUNTIME_CANDIDATES_V2 ===")
    print("mode=research_only")
    print(f"expanded_runtime_candidate_rows={saved}")
    print("runtime_allowed=0")
    print("execution_allowed=0")
    print("micro_live_allowed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("next=EXPANDED_EDGE_DISCOVERY_V2_REPORT")
    print("VERDICT=EXPANDED_RUNTIME_CANDIDATES_V2_READY")


if __name__ == "__main__":
    main()
