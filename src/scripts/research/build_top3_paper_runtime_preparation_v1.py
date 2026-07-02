from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics_global_edge_top3_paper_runtime_preparation_v1 (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    rank_no BIGINT NOT NULL,
                    symbol TEXT NOT NULL,
                    asset_class TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    strategy_family TEXT NOT NULL,
                    regime TEXT NOT NULL,
                    oos_status TEXT NOT NULL,
                    preparation_status TEXT NOT NULL,
                    runtime_allowed BOOLEAN NOT NULL DEFAULT false,
                    execution_allowed BOOLEAN NOT NULL DEFAULT false,
                    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,
                    UNIQUE(symbol, timeframe, strategy_family, regime)
                );
            """)

            cur.execute("""
                SELECT rank_no, symbol, asset_class, timeframe, strategy_family, regime, oos_status
                FROM analytics_global_edge_top3_oos_validation_v1
                WHERE oos_status='OOS_PASS'
                ORDER BY rank_no
                LIMIT 3;
            """)
            rows = cur.fetchall()

            saved = 0

            for row in rows:
                cur.execute("""
                    INSERT INTO analytics_global_edge_top3_paper_runtime_preparation_v1
                    (
                        rank_no, symbol, asset_class, timeframe, strategy_family, regime,
                        oos_status, preparation_status,
                        runtime_allowed, execution_allowed, micro_live_allowed
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,'PAPER_PREPARED',false,false,false)
                    ON CONFLICT (symbol, timeframe, strategy_family, regime)
                    DO UPDATE SET
                        created_at = now(),
                        rank_no = EXCLUDED.rank_no,
                        asset_class = EXCLUDED.asset_class,
                        oos_status = EXCLUDED.oos_status,
                        preparation_status = EXCLUDED.preparation_status,
                        runtime_allowed = false,
                        execution_allowed = false,
                        micro_live_allowed = false;
                """, row)
                saved += 1

    print("=== TOP3_PAPER_RUNTIME_PREPARATION_V1 ===")
    print("mode=research_only")
    print(f"prepared_rows={saved}")
    print("preparation_status=PAPER_PREPARED")
    print("runtime_allowed=0")
    print("execution_allowed=0")
    print("micro_live_allowed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("next=TOP3_SHADOW_RUNTIME_PLAN_V1")
    print("VERDICT=TOP3_PAPER_RUNTIME_PREPARATION_V1_READY")


if __name__ == "__main__":
    main()
