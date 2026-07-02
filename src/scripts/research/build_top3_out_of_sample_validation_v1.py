from __future__ import annotations

import os
from decimal import Decimal

import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def ensure_schema() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics_global_edge_top3_oos_validation_v1 (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    rank_no BIGINT NOT NULL,
                    symbol TEXT NOT NULL,
                    asset_class TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    strategy_family TEXT NOT NULL,
                    regime TEXT NOT NULL,
                    trades_count BIGINT NOT NULL DEFAULT 0,
                    in_sample_expectancy NUMERIC NOT NULL DEFAULT 0,
                    oos_expectancy NUMERIC NOT NULL DEFAULT 0,
                    in_sample_profit_factor NUMERIC NOT NULL DEFAULT 0,
                    oos_profit_factor NUMERIC NOT NULL DEFAULT 0,
                    oos_degradation_pct NUMERIC NOT NULL DEFAULT 0,
                    oos_status TEXT NOT NULL,
                    runtime_allowed BOOLEAN NOT NULL DEFAULT false,
                    execution_allowed BOOLEAN NOT NULL DEFAULT false,
                    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,
                    UNIQUE(symbol, timeframe, strategy_family, regime)
                );
            """)


def main() -> None:
    ensure_schema()

    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    r.rank_no,
                    r.symbol,
                    r.asset_class,
                    r.timeframe,
                    r.strategy_family,
                    r.regime,
                    r.trades_count,
                    r.expectancy,
                    r.profit_factor,
                    wf.test_expectancy,
                    wf.test_profit_factor
                FROM analytics_global_edge_expanded_ranking_v2 r
                JOIN analytics_global_edge_expanded_walk_forward_v2 wf
                  ON wf.symbol=r.symbol
                 AND wf.timeframe=r.timeframe
                 AND wf.strategy_family=r.strategy_family
                 AND wf.regime=r.regime
                WHERE r.status='CANDIDATE'
                  AND wf.walk_forward_status='WALK_FORWARD_PASS'
                ORDER BY r.edge_score DESC, r.trades_count DESC
                LIMIT 3;
            """)
            rows = cur.fetchall()

            saved = 0
            passed = 0
            rejected = 0

            for row in rows:
                (
                    rank_no, symbol, asset_class, timeframe, strategy_family, regime,
                    trades, ins_exp, ins_pf, oos_exp, oos_pf,
                ) = row

                ins_exp_d = Decimal(str(ins_exp or 0))
                oos_exp_d = Decimal(str(oos_exp or 0))
                ins_pf_d = Decimal(str(ins_pf or 0))
                oos_pf_d = Decimal(str(oos_pf or 0))

                degradation = (
                    Decimal("100")
                    if ins_exp_d == 0
                    else abs((ins_exp_d - oos_exp_d) / ins_exp_d * Decimal("100"))
                )

                oos_status = (
                    "OOS_PASS"
                    if trades >= 100
                    and oos_exp_d > 0
                    and oos_pf_d >= Decimal("1.05")
                    and degradation <= Decimal("40")
                    else "OOS_REJECT"
                )

                if oos_status == "OOS_PASS":
                    passed += 1
                else:
                    rejected += 1

                cur.execute("""
                    INSERT INTO analytics_global_edge_top3_oos_validation_v1
                    (
                        rank_no,
                        symbol,
                        asset_class,
                        timeframe,
                        strategy_family,
                        regime,
                        trades_count,
                        in_sample_expectancy,
                        oos_expectancy,
                        in_sample_profit_factor,
                        oos_profit_factor,
                        oos_degradation_pct,
                        oos_status,
                        runtime_allowed,
                        execution_allowed,
                        micro_live_allowed
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false,false,false)
                    ON CONFLICT (symbol, timeframe, strategy_family, regime)
                    DO UPDATE SET
                        created_at = now(),
                        rank_no = EXCLUDED.rank_no,
                        asset_class = EXCLUDED.asset_class,
                        trades_count = EXCLUDED.trades_count,
                        in_sample_expectancy = EXCLUDED.in_sample_expectancy,
                        oos_expectancy = EXCLUDED.oos_expectancy,
                        in_sample_profit_factor = EXCLUDED.in_sample_profit_factor,
                        oos_profit_factor = EXCLUDED.oos_profit_factor,
                        oos_degradation_pct = EXCLUDED.oos_degradation_pct,
                        oos_status = EXCLUDED.oos_status,
                        runtime_allowed = false,
                        execution_allowed = false,
                        micro_live_allowed = false;
                """, (
                    rank_no, symbol, asset_class, timeframe, strategy_family, regime,
                    trades, ins_exp_d, oos_exp_d, ins_pf_d, oos_pf_d, degradation, oos_status,
                ))
                saved += 1

    print("=== TOP3_OUT_OF_SAMPLE_VALIDATION_V1 ===")
    print("mode=research_only")
    print(f"top3_oos_rows={saved}")
    print(f"oos_pass={passed}")
    print(f"oos_reject={rejected}")
    print("runtime_allowed=0")
    print("execution_allowed=0")
    print("micro_live_allowed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("next=TOP3_PAPER_RUNTIME_PREPARATION_V1")
    print("VERDICT=TOP3_OUT_OF_SAMPLE_VALIDATION_V1_READY")


if __name__ == "__main__":
    main()
