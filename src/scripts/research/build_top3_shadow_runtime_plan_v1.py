from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics_global_edge_top3_shadow_runtime_plan_v1 (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    rank_no BIGINT NOT NULL,
                    symbol TEXT NOT NULL,
                    asset_class TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    strategy_family TEXT NOT NULL,
                    regime TEXT NOT NULL,
                    shadow_status TEXT NOT NULL,
                    observation_days INT NOT NULL,
                    max_risk_per_trade_pct NUMERIC NOT NULL,
                    daily_loss_limit_pct NUMERIC NOT NULL,
                    max_shadow_trades INT NOT NULL,
                    promotion_rule TEXT NOT NULL,
                    stop_rule TEXT NOT NULL,
                    runtime_allowed BOOLEAN NOT NULL DEFAULT false,
                    execution_allowed BOOLEAN NOT NULL DEFAULT false,
                    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,
                    UNIQUE(symbol, timeframe, strategy_family, regime)
                );
            """)

            cur.execute("""
                SELECT rank_no, symbol, asset_class, timeframe, strategy_family, regime
                FROM analytics_global_edge_top3_paper_runtime_preparation_v1
                WHERE preparation_status='PAPER_PREPARED'
                ORDER BY rank_no
                LIMIT 3;
            """)
            rows = cur.fetchall()

            saved = 0

            for row in rows:
                cur.execute("""
                    INSERT INTO analytics_global_edge_top3_shadow_runtime_plan_v1
                    (
                        rank_no,
                        symbol,
                        asset_class,
                        timeframe,
                        strategy_family,
                        regime,
                        shadow_status,
                        observation_days,
                        max_risk_per_trade_pct,
                        daily_loss_limit_pct,
                        max_shadow_trades,
                        promotion_rule,
                        stop_rule,
                        runtime_allowed,
                        execution_allowed,
                        micro_live_allowed
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,
                        'SHADOW_PLANNED',
                        30,
                        0.25,
                        1.00,
                        100,
                        'GO_PAPER only if shadow expectancy > 0, PF >= 1.10, drawdown within limit, no risk breach',
                        'STOP if daily loss limit breached, PF < 1.00, expectancy <= 0, or risk event occurs',
                        false,false,false
                    )
                    ON CONFLICT (symbol, timeframe, strategy_family, regime)
                    DO UPDATE SET
                        created_at = now(),
                        rank_no = EXCLUDED.rank_no,
                        asset_class = EXCLUDED.asset_class,
                        shadow_status = EXCLUDED.shadow_status,
                        observation_days = EXCLUDED.observation_days,
                        max_risk_per_trade_pct = EXCLUDED.max_risk_per_trade_pct,
                        daily_loss_limit_pct = EXCLUDED.daily_loss_limit_pct,
                        max_shadow_trades = EXCLUDED.max_shadow_trades,
                        promotion_rule = EXCLUDED.promotion_rule,
                        stop_rule = EXCLUDED.stop_rule,
                        runtime_allowed = false,
                        execution_allowed = false,
                        micro_live_allowed = false;
                """, row)
                saved += 1

    print("=== TOP3_SHADOW_RUNTIME_PLAN_V1 ===")
    print("mode=shadow_plan_only")
    print(f"planned_rows={saved}")
    print("shadow_status=SHADOW_PLANNED")
    print("observation_days=30")
    print("max_risk_per_trade_pct=0.25")
    print("daily_loss_limit_pct=1.00")
    print("runtime_allowed=0")
    print("execution_allowed=0")
    print("micro_live_allowed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("next=TOP3_SHADOW_RUNTIME_EXECUTION_V1")
    print("VERDICT=TOP3_SHADOW_RUNTIME_PLAN_V1_READY")


if __name__ == "__main__":
    main()
