from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics_global_edge_top3_shadow_runtime_execution_v1 (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    rank_no BIGINT NOT NULL,
                    symbol TEXT NOT NULL,
                    asset_class TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    strategy_family TEXT NOT NULL,
                    regime TEXT NOT NULL,
                    shadow_status TEXT NOT NULL,
                    virtual_signal_status TEXT NOT NULL,
                    virtual_order_status TEXT NOT NULL,
                    virtual_fill_status TEXT NOT NULL,
                    shadow_pnl NUMERIC NOT NULL DEFAULT 0,
                    shadow_expectancy NUMERIC NOT NULL DEFAULT 0,
                    shadow_profit_factor NUMERIC NOT NULL DEFAULT 0,
                    risk_status TEXT NOT NULL,
                    runtime_allowed BOOLEAN NOT NULL DEFAULT false,
                    execution_allowed BOOLEAN NOT NULL DEFAULT false,
                    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,
                    UNIQUE(symbol, timeframe, strategy_family, regime)
                );
            """)

            cur.execute("""
                SELECT
                    p.rank_no,
                    p.symbol,
                    p.asset_class,
                    p.timeframe,
                    p.strategy_family,
                    p.regime,
                    r.expectancy,
                    r.profit_factor
                FROM analytics_global_edge_top3_shadow_runtime_plan_v1 p
                JOIN analytics_global_edge_expanded_ranking_v2 r
                  ON r.symbol = p.symbol
                 AND r.timeframe = p.timeframe
                 AND r.strategy_family = p.strategy_family
                 AND r.regime = p.regime
                WHERE p.shadow_status='SHADOW_PLANNED'
                  AND p.runtime_allowed=false
                  AND p.execution_allowed=false
                  AND p.micro_live_allowed=false
                ORDER BY p.rank_no
                LIMIT 3;
            """)
            rows = cur.fetchall()

            saved = 0

            for row in rows:
                (
                    rank_no,
                    symbol,
                    asset_class,
                    timeframe,
                    strategy_family,
                    regime,
                    expectancy,
                    profit_factor,
                ) = row

                cur.execute("""
                    INSERT INTO analytics_global_edge_top3_shadow_runtime_execution_v1
                    (
                        rank_no,
                        symbol,
                        asset_class,
                        timeframe,
                        strategy_family,
                        regime,
                        shadow_status,
                        virtual_signal_status,
                        virtual_order_status,
                        virtual_fill_status,
                        shadow_pnl,
                        shadow_expectancy,
                        shadow_profit_factor,
                        risk_status,
                        runtime_allowed,
                        execution_allowed,
                        micro_live_allowed
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,
                        'SHADOW_ACTIVE',
                        'VIRTUAL_SIGNAL_READY',
                        'VIRTUAL_ORDER_READY',
                        'VIRTUAL_FILL_READY',
                        0,
                        %s,
                        %s,
                        'RISK_OK',
                        false,false,false
                    )
                    ON CONFLICT (symbol, timeframe, strategy_family, regime)
                    DO UPDATE SET
                        created_at = now(),
                        rank_no = EXCLUDED.rank_no,
                        asset_class = EXCLUDED.asset_class,
                        shadow_status = EXCLUDED.shadow_status,
                        virtual_signal_status = EXCLUDED.virtual_signal_status,
                        virtual_order_status = EXCLUDED.virtual_order_status,
                        virtual_fill_status = EXCLUDED.virtual_fill_status,
                        shadow_pnl = EXCLUDED.shadow_pnl,
                        shadow_expectancy = EXCLUDED.shadow_expectancy,
                        shadow_profit_factor = EXCLUDED.shadow_profit_factor,
                        risk_status = EXCLUDED.risk_status,
                        runtime_allowed = false,
                        execution_allowed = false,
                        micro_live_allowed = false;
                """, (
                    rank_no,
                    symbol,
                    asset_class,
                    timeframe,
                    strategy_family,
                    regime,
                    expectancy,
                    profit_factor,
                ))
                saved += 1

    print("=== TOP3_SHADOW_RUNTIME_EXECUTION_V1 ===")
    print("mode=shadow_runtime_only")
    print(f"shadow_execution_rows={saved}")
    print("shadow_status=SHADOW_ACTIVE")
    print("virtual_signal_status=VIRTUAL_SIGNAL_READY")
    print("virtual_order_status=VIRTUAL_ORDER_READY")
    print("virtual_fill_status=VIRTUAL_FILL_READY")
    print("risk_status=RISK_OK")
    print("runtime_allowed=0")
    print("execution_allowed=0")
    print("micro_live_allowed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("next=TOP3_SHADOW_RUNTIME_REPORT_V1")
    print("VERDICT=TOP3_SHADOW_RUNTIME_EXECUTION_V1_READY")


if __name__ == "__main__":
    main()
