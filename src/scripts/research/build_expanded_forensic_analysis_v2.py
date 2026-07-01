from __future__ import annotations

import os
from decimal import Decimal

import psycopg2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def ensure_schema() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics_global_edge_expanded_forensic_v2 (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    symbol TEXT NOT NULL,
                    asset_class TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    strategy_family TEXT NOT NULL,
                    regime TEXT NOT NULL,
                    rank_no BIGINT NOT NULL,
                    trades_count BIGINT NOT NULL DEFAULT 0,
                    expectancy NUMERIC NOT NULL DEFAULT 0,
                    profit_factor NUMERIC NOT NULL DEFAULT 0,
                    edge_score NUMERIC NOT NULL DEFAULT 0,
                    sample_status TEXT NOT NULL,
                    pnl_status TEXT NOT NULL,
                    pf_status TEXT NOT NULL,
                    forensic_status TEXT NOT NULL,
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
                SELECT symbol, asset_class, timeframe, strategy_family, regime,
                       rank_no, trades_count, expectancy, profit_factor, edge_score
                FROM analytics_global_edge_expanded_ranking_v2
                ORDER BY rank_no;
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
                    rank_no,
                    trades_count,
                    expectancy,
                    profit_factor,
                    edge_score,
                ) = row

                trades = int(trades_count or 0)
                exp = Decimal(str(expectancy or 0))
                pf = Decimal(str(profit_factor or 0))
                score = Decimal(str(edge_score or 0))

                sample_status = "OK" if trades >= 30 else "LOW_SAMPLE"
                pnl_status = "OK" if exp > 0 else "NEGATIVE_OR_ZERO"
                pf_status = "OK" if pf >= Decimal("1.05") else "WEAK_PF"

                forensic_status = (
                    "FORENSIC_PASS"
                    if sample_status == "OK"
                    and pnl_status == "OK"
                    and pf_status == "OK"
                    and score > 0
                    else "FORENSIC_REJECT"
                )

                cur.execute("""
                    INSERT INTO analytics_global_edge_expanded_forensic_v2
                    (
                        symbol,
                        asset_class,
                        timeframe,
                        strategy_family,
                        regime,
                        rank_no,
                        trades_count,
                        expectancy,
                        profit_factor,
                        edge_score,
                        sample_status,
                        pnl_status,
                        pf_status,
                        forensic_status,
                        runtime_allowed,
                        execution_allowed,
                        micro_live_allowed
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false,false,false)
                    ON CONFLICT (symbol, timeframe, strategy_family, regime)
                    DO UPDATE SET
                        created_at = now(),
                        asset_class = EXCLUDED.asset_class,
                        rank_no = EXCLUDED.rank_no,
                        trades_count = EXCLUDED.trades_count,
                        expectancy = EXCLUDED.expectancy,
                        profit_factor = EXCLUDED.profit_factor,
                        edge_score = EXCLUDED.edge_score,
                        sample_status = EXCLUDED.sample_status,
                        pnl_status = EXCLUDED.pnl_status,
                        pf_status = EXCLUDED.pf_status,
                        forensic_status = EXCLUDED.forensic_status,
                        runtime_allowed = false,
                        execution_allowed = false,
                        micro_live_allowed = false;
                """, (
                    symbol,
                    asset_class,
                    timeframe,
                    strategy_family,
                    regime,
                    rank_no,
                    trades,
                    exp,
                    pf,
                    score,
                    sample_status,
                    pnl_status,
                    pf_status,
                    forensic_status,
                ))
                saved += 1

    print("=== EXPANDED_FORENSIC_ANALYSIS_V2 ===")
    print("mode=research_only")
    print(f"expanded_forensic_rows={saved}")
    print("matrix_scope=symbol_timeframe_strategy_regime")
    print("runtime_allowed=0")
    print("execution_allowed=0")
    print("micro_live_allowed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("next=EXPANDED_ROBUSTNESS_TEST_V2")
    print("VERDICT=EXPANDED_FORENSIC_ANALYSIS_V2_READY")


if __name__ == "__main__":
    main()
