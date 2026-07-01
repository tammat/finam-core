from __future__ import annotations

import os
import psycopg2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

STRATEGY_FAMILIES = [
    "BREAKOUT",
    "MEAN_REVERSION",
    "TREND_FOLLOWING",
    "VOLATILITY_EXPANSION",
]


def ensure_schema() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics_global_edge_strategy_matrix_v2 (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    symbol TEXT NOT NULL,
                    asset_class TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    strategy_family TEXT NOT NULL,
                    status TEXT NOT NULL,
                    runtime_allowed BOOLEAN NOT NULL DEFAULT false,
                    execution_allowed BOOLEAN NOT NULL DEFAULT false,
                    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,
                    UNIQUE(symbol, timeframe, strategy_family)
                );
            """)


def main() -> None:
    ensure_schema()

    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT symbol, asset_class, timeframe
                FROM analytics_global_edge_universe_timeframe_v2
                WHERE status='READY'
                ORDER BY symbol, timeframe;
            """)
            rows = cur.fetchall()

            saved = 0

            for symbol, asset_class, timeframe in rows:
                for strategy_family in STRATEGY_FAMILIES:
                    cur.execute("""
                        INSERT INTO analytics_global_edge_strategy_matrix_v2
                        (
                            symbol,
                            asset_class,
                            timeframe,
                            strategy_family,
                            status,
                            runtime_allowed,
                            execution_allowed,
                            micro_live_allowed
                        )
                        VALUES (%s,%s,%s,%s,'READY',false,false,false)
                        ON CONFLICT (symbol, timeframe, strategy_family)
                        DO UPDATE SET
                            created_at = now(),
                            asset_class = EXCLUDED.asset_class,
                            status = EXCLUDED.status,
                            runtime_allowed = false,
                            execution_allowed = false,
                            micro_live_allowed = false;
                    """, (symbol, asset_class, timeframe, strategy_family))
                    saved += 1

    print("=== STRATEGY_FAMILY_MATRIX_V1 ===")
    print("mode=research_only")
    print(f"matrix_rows={saved}")
    print("strategy_families=BREAKOUT,MEAN_REVERSION,TREND_FOLLOWING,VOLATILITY_EXPANSION")
    print("runtime_allowed=0")
    print("execution_allowed=0")
    print("micro_live_allowed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("next=REGIME_MATRIX_V1")
    print("VERDICT=STRATEGY_FAMILY_MATRIX_V1_READY")


if __name__ == "__main__":
    main()
