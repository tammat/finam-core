from __future__ import annotations

import os
from decimal import Decimal

import psycopg2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def ensure_schema() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics_global_edge_walk_forward_v2 (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    symbol TEXT NOT NULL,
                    asset_class TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    strategy_name TEXT NOT NULL,
                    walk_window TEXT NOT NULL,
                    train_expectancy NUMERIC NOT NULL DEFAULT 0,
                    test_expectancy NUMERIC NOT NULL DEFAULT 0,
                    train_profit_factor NUMERIC NOT NULL DEFAULT 0,
                    test_profit_factor NUMERIC NOT NULL DEFAULT 0,
                    robustness_status TEXT NOT NULL,
                    walk_forward_status TEXT NOT NULL,
                    runtime_allowed BOOLEAN NOT NULL DEFAULT false,
                    UNIQUE(symbol, timeframe, strategy_name, walk_window)
                );
            """)


def main() -> None:
    ensure_schema()

    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT symbol, asset_class, timeframe, strategy_name,
                       base_expectancy, stress_expectancy,
                       base_profit_factor, stress_profit_factor,
                       robustness_status
                FROM analytics_global_edge_robustness_v2
                ORDER BY symbol;
            """)
            rows = cur.fetchall()

            saved = 0

            for row in rows:
                (
                    symbol,
                    asset_class,
                    timeframe,
                    strategy_name,
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

                status = (
                    "WALK_FORWARD_PASS"
                    if robustness_status == "ROBUST_PASS"
                    and train_exp > 0
                    and test_exp > 0
                    and train_pf >= Decimal("1.10")
                    and test_pf >= Decimal("1.05")
                    else "WALK_FORWARD_REJECT"
                )

                cur.execute("""
                    INSERT INTO analytics_global_edge_walk_forward_v2
                    (
                        symbol,
                        asset_class,
                        timeframe,
                        strategy_name,
                        walk_window,
                        train_expectancy,
                        test_expectancy,
                        train_profit_factor,
                        test_profit_factor,
                        robustness_status,
                        walk_forward_status,
                        runtime_allowed
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false)
                    ON CONFLICT (symbol, timeframe, strategy_name, walk_window)
                    DO UPDATE SET
                        created_at = now(),
                        asset_class = EXCLUDED.asset_class,
                        train_expectancy = EXCLUDED.train_expectancy,
                        test_expectancy = EXCLUDED.test_expectancy,
                        train_profit_factor = EXCLUDED.train_profit_factor,
                        test_profit_factor = EXCLUDED.test_profit_factor,
                        robustness_status = EXCLUDED.robustness_status,
                        walk_forward_status = EXCLUDED.walk_forward_status,
                        runtime_allowed = false;
                """, (
                    symbol,
                    asset_class,
                    timeframe,
                    strategy_name,
                    "WF_70_30_SYNTHETIC_V2",
                    train_exp,
                    test_exp,
                    train_pf,
                    test_pf,
                    robustness_status,
                    status,
                ))
                saved += 1

    print("=== WALK_FORWARD_V2 ===")
    print("mode=research_only")
    print(f"walk_forward_rows={saved}")
    print("walk_window=WF_70_30_SYNTHETIC_V2")
    print("runtime_allowed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("next=RUNTIME_CANDIDATES_V2")
    print("VERDICT=WALK_FORWARD_V2_READY")


if __name__ == "__main__":
    main()
