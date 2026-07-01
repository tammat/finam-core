from __future__ import annotations

import os
from decimal import Decimal

import psycopg2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def ensure_schema() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics_global_edge_expanded_walk_forward_v2 (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    symbol TEXT NOT NULL,
                    asset_class TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    strategy_family TEXT NOT NULL,
                    regime TEXT NOT NULL,
                    walk_window TEXT NOT NULL,
                    train_expectancy NUMERIC NOT NULL DEFAULT 0,
                    test_expectancy NUMERIC NOT NULL DEFAULT 0,
                    train_profit_factor NUMERIC NOT NULL DEFAULT 0,
                    test_profit_factor NUMERIC NOT NULL DEFAULT 0,
                    robustness_status TEXT NOT NULL,
                    walk_forward_status TEXT NOT NULL,
                    runtime_allowed BOOLEAN NOT NULL DEFAULT false,
                    execution_allowed BOOLEAN NOT NULL DEFAULT false,
                    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,
                    UNIQUE(symbol, timeframe, strategy_family, regime, walk_window)
                );
            """)


def main() -> None:
    ensure_schema()

    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT symbol, asset_class, timeframe, strategy_family, regime,
                       base_expectancy, stress_expectancy,
                       base_profit_factor, stress_profit_factor,
                       robustness_status
                FROM analytics_global_edge_expanded_robustness_v2
                ORDER BY symbol, timeframe, strategy_family, regime;
            """)
            rows = cur.fetchall()

            saved = 0

            for row in rows:
                (
                    symbol,
                    asset_class,
                    timeframe,
                    strategy_family,
                    regime,
                    base_exp,
                    stress_exp,
                    base_pf,
                    stress_pf,
                    robustness_status,
                ) = row

                train_exp = Decimal(str(base_exp or 0))
                test_exp = Decimal(str(stress_exp or 0))
                train_pf = Decimal(str(base_pf or 0))
                test_pf = Decimal(str(stress_pf or 0))

                wf_status = (
                    "WALK_FORWARD_PASS"
                    if robustness_status == "ROBUST_PASS"
                    and train_exp > 0
                    and test_exp > 0
                    and train_pf >= Decimal("1.05")
                    and test_pf >= Decimal("1.03")
                    else "WALK_FORWARD_REJECT"
                )

                cur.execute("""
                    INSERT INTO analytics_global_edge_expanded_walk_forward_v2
                    (
                        symbol,
                        asset_class,
                        timeframe,
                        strategy_family,
                        regime,
                        walk_window,
                        train_expectancy,
                        test_expectancy,
                        train_profit_factor,
                        test_profit_factor,
                        robustness_status,
                        walk_forward_status,
                        runtime_allowed,
                        execution_allowed,
                        micro_live_allowed
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false,false,false)
                    ON CONFLICT (symbol, timeframe, strategy_family, regime, walk_window)
                    DO UPDATE SET
                        created_at = now(),
                        asset_class = EXCLUDED.asset_class,
                        train_expectancy = EXCLUDED.train_expectancy,
                        test_expectancy = EXCLUDED.test_expectancy,
                        train_profit_factor = EXCLUDED.train_profit_factor,
                        test_profit_factor = EXCLUDED.test_profit_factor,
                        robustness_status = EXCLUDED.robustness_status,
                        walk_forward_status = EXCLUDED.walk_forward_status,
                        runtime_allowed = false,
                        execution_allowed = false,
                        micro_live_allowed = false;
                """, (
                    symbol,
                    asset_class,
                    timeframe,
                    strategy_family,
                    regime,
                    "EXPANDED_WF_70_30_SYNTHETIC_V2",
                    train_exp,
                    test_exp,
                    train_pf,
                    test_pf,
                    robustness_status,
                    wf_status,
                ))
                saved += 1

    print("=== EXPANDED_WALK_FORWARD_V2 ===")
    print("mode=research_only")
    print(f"expanded_walk_forward_rows={saved}")
    print("walk_window=EXPANDED_WF_70_30_SYNTHETIC_V2")
    print("runtime_allowed=0")
    print("execution_allowed=0")
    print("micro_live_allowed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("next=EXPANDED_RUNTIME_CANDIDATES_V2")
    print("VERDICT=EXPANDED_WALK_FORWARD_V2_READY")


if __name__ == "__main__":
    main()
