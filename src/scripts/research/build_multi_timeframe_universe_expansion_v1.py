from __future__ import annotations

import os
import psycopg2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

TIMEFRAMES = ["M1", "M5", "M15", "H1"]


def ensure_schema() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics_global_edge_universe_timeframe_v2 (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    symbol TEXT NOT NULL,
                    asset_class TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    source TEXT NOT NULL,
                    status TEXT NOT NULL,
                    runtime_allowed BOOLEAN NOT NULL DEFAULT false,
                    execution_allowed BOOLEAN NOT NULL DEFAULT false,
                    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,
                    UNIQUE(symbol, timeframe, source)
                );
            """)


def main() -> None:
    ensure_schema()

    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT symbol, asset_class, source
                FROM analytics_global_edge_universe_v2
                WHERE status='READY'
                ORDER BY symbol;
            """)
            rows = cur.fetchall()

            saved = 0

            for symbol, asset_class, source in rows:
                for timeframe in TIMEFRAMES:
                    cur.execute("""
                        INSERT INTO analytics_global_edge_universe_timeframe_v2
                        (
                            symbol,
                            asset_class,
                            timeframe,
                            source,
                            status,
                            runtime_allowed,
                            execution_allowed,
                            micro_live_allowed
                        )
                        VALUES (%s,%s,%s,%s,'READY',false,false,false)
                        ON CONFLICT (symbol, timeframe, source)
                        DO UPDATE SET
                            created_at = now(),
                            asset_class = EXCLUDED.asset_class,
                            status = EXCLUDED.status,
                            runtime_allowed = false,
                            execution_allowed = false,
                            micro_live_allowed = false;
                    """, (symbol, asset_class, timeframe, source))
                    saved += 1

    print("=== MULTI_TIMEFRAME_UNIVERSE_EXPANSION_V1 ===")
    print("mode=research_only")
    print(f"expanded_rows={saved}")
    print("timeframes=M1,M5,M15,H1")
    print("runtime_allowed=0")
    print("execution_allowed=0")
    print("micro_live_allowed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("next=STRATEGY_FAMILY_MATRIX_V1")
    print("VERDICT=MULTI_TIMEFRAME_UNIVERSE_EXPANSION_V1_READY")


if __name__ == "__main__":
    main()
