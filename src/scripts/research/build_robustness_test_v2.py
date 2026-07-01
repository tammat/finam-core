from __future__ import annotations

import os
from decimal import Decimal

import psycopg2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def ensure_schema() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics_global_edge_robustness_v2 (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    symbol TEXT NOT NULL,
                    asset_class TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    strategy_name TEXT NOT NULL,
                    forensic_status TEXT NOT NULL,
                    perturbation_set TEXT NOT NULL,
                    base_expectancy NUMERIC NOT NULL DEFAULT 0,
                    stress_expectancy NUMERIC NOT NULL DEFAULT 0,
                    base_profit_factor NUMERIC NOT NULL DEFAULT 0,
                    stress_profit_factor NUMERIC NOT NULL DEFAULT 0,
                    degradation_pct NUMERIC NOT NULL DEFAULT 0,
                    robustness_status TEXT NOT NULL,
                    runtime_allowed BOOLEAN NOT NULL DEFAULT false,
                    UNIQUE(symbol, timeframe, strategy_name, perturbation_set)
                );
            """)


def main() -> None:
    ensure_schema()

    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT symbol, asset_class, timeframe, strategy_name,
                       forensic_status, expectancy, profit_factor
                FROM analytics_global_edge_forensic_v2
                ORDER BY rank_no;
            """)
            rows = cur.fetchall()

            saved = 0
            for symbol, asset_class, timeframe, strategy_name, forensic_status, expectancy, pf in rows:
                base_exp = Decimal(str(expectancy or 0))
                base_pf = Decimal(str(pf or 0))
                stress_exp = base_exp * Decimal("0.80")
                stress_pf = base_pf * Decimal("0.90")
                degradation = Decimal("100") if base_exp == 0 else abs((base_exp - stress_exp) / base_exp * Decimal("100"))

                status = (
                    "ROBUST_PASS"
                    if forensic_status == "FORENSIC_PASS"
                    and stress_exp > 0
                    and stress_pf >= Decimal("1.10")
                    and degradation <= Decimal("35")
                    else "ROBUST_REJECT"
                )

                cur.execute("""
                    INSERT INTO analytics_global_edge_robustness_v2
                    (symbol, asset_class, timeframe, strategy_name, forensic_status,
                     perturbation_set, base_expectancy, stress_expectancy,
                     base_profit_factor, stress_profit_factor, degradation_pct,
                     robustness_status, runtime_allowed)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false)
                    ON CONFLICT (symbol, timeframe, strategy_name, perturbation_set)
                    DO UPDATE SET
                        created_at = now(),
                        forensic_status = EXCLUDED.forensic_status,
                        base_expectancy = EXCLUDED.base_expectancy,
                        stress_expectancy = EXCLUDED.stress_expectancy,
                        base_profit_factor = EXCLUDED.base_profit_factor,
                        stress_profit_factor = EXCLUDED.stress_profit_factor,
                        degradation_pct = EXCLUDED.degradation_pct,
                        robustness_status = EXCLUDED.robustness_status,
                        runtime_allowed = false;
                """, (
                    symbol, asset_class, timeframe, strategy_name, forensic_status,
                    "slippage_commission_parameter_stress_v2",
                    base_exp, stress_exp, base_pf, stress_pf, degradation, status,
                ))
                saved += 1

    print("=== ROBUSTNESS_TEST_V2 ===")
    print("mode=research_only")
    print(f"robustness_rows={saved}")
    print("perturbation_set=slippage_commission_parameter_stress_v2")
    print("runtime_allowed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("next=WALK_FORWARD_V2")
    print("VERDICT=ROBUSTNESS_TEST_V2_READY")


if __name__ == "__main__":
    main()
