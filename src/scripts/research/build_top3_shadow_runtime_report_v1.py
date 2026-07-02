from __future__ import annotations

import os
from decimal import Decimal

import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics_global_edge_top3_shadow_runtime_report_v1 (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    rank_no BIGINT NOT NULL,
                    symbol TEXT NOT NULL,
                    asset_class TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    strategy_family TEXT NOT NULL,
                    regime TEXT NOT NULL,
                    shadow_status TEXT NOT NULL,
                    shadow_pnl NUMERIC NOT NULL DEFAULT 0,
                    shadow_expectancy NUMERIC NOT NULL DEFAULT 0,
                    shadow_profit_factor NUMERIC NOT NULL DEFAULT 0,
                    risk_status TEXT NOT NULL,
                    report_status TEXT NOT NULL,
                    recommendation TEXT NOT NULL,
                    runtime_allowed BOOLEAN NOT NULL DEFAULT false,
                    execution_allowed BOOLEAN NOT NULL DEFAULT false,
                    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,
                    UNIQUE(symbol, timeframe, strategy_family, regime)
                );
            """)

            cur.execute("""
                SELECT
                    rank_no,
                    symbol,
                    asset_class,
                    timeframe,
                    strategy_family,
                    regime,
                    shadow_status,
                    shadow_pnl,
                    shadow_expectancy,
                    shadow_profit_factor,
                    risk_status
                FROM analytics_global_edge_top3_shadow_runtime_execution_v1
                WHERE shadow_status='SHADOW_ACTIVE'
                  AND runtime_allowed=false
                  AND execution_allowed=false
                  AND micro_live_allowed=false
                ORDER BY rank_no
                LIMIT 3;
            """)
            rows = cur.fetchall()

            saved = 0
            go_paper = 0
            keep_shadow = 0
            rejected = 0

            print("=== TOP3_SHADOW_RUNTIME_REPORT_V1 ===")
            print("mode=shadow_report_only")

            for row in rows:
                (
                    rank_no,
                    symbol,
                    asset_class,
                    timeframe,
                    strategy_family,
                    regime,
                    shadow_status,
                    shadow_pnl,
                    shadow_expectancy,
                    shadow_profit_factor,
                    risk_status,
                ) = row

                exp = Decimal(str(shadow_expectancy or 0))
                pf = Decimal(str(shadow_profit_factor or 0))

                if risk_status != "RISK_OK":
                    recommendation = "REJECT"
                    report_status = "RISK_REJECT"
                    rejected += 1
                elif exp > 0 and pf >= Decimal("1.10"):
                    recommendation = "GO_PAPER"
                    report_status = "SHADOW_PASS"
                    go_paper += 1
                elif exp > 0 and pf >= Decimal("1.00"):
                    recommendation = "KEEP_SHADOW"
                    report_status = "SHADOW_OBSERVE"
                    keep_shadow += 1
                else:
                    recommendation = "REJECT"
                    report_status = "SHADOW_REJECT"
                    rejected += 1

                cur.execute("""
                    INSERT INTO analytics_global_edge_top3_shadow_runtime_report_v1
                    (
                        rank_no,
                        symbol,
                        asset_class,
                        timeframe,
                        strategy_family,
                        regime,
                        shadow_status,
                        shadow_pnl,
                        shadow_expectancy,
                        shadow_profit_factor,
                        risk_status,
                        report_status,
                        recommendation,
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
                        shadow_status = EXCLUDED.shadow_status,
                        shadow_pnl = EXCLUDED.shadow_pnl,
                        shadow_expectancy = EXCLUDED.shadow_expectancy,
                        shadow_profit_factor = EXCLUDED.shadow_profit_factor,
                        risk_status = EXCLUDED.risk_status,
                        report_status = EXCLUDED.report_status,
                        recommendation = EXCLUDED.recommendation,
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
                    shadow_status,
                    shadow_pnl,
                    exp,
                    pf,
                    risk_status,
                    report_status,
                    recommendation,
                ))
                saved += 1

                print(
                    "SHADOW_REPORT_ROW "
                    f"rank_no={rank_no} symbol={symbol} asset_class={asset_class} "
                    f"timeframe={timeframe} strategy_family={strategy_family} regime={regime} "
                    f"shadow_status={shadow_status} shadow_pnl={shadow_pnl} "
                    f"shadow_expectancy={exp} shadow_profit_factor={pf} "
                    f"risk_status={risk_status} report_status={report_status} "
                    f"recommendation={recommendation}"
                )

    print(f"report_rows={saved}")
    print(f"go_paper={go_paper}")
    print(f"keep_shadow={keep_shadow}")
    print(f"rejected={rejected}")
    print("runtime_allowed=0")
    print("execution_allowed=0")
    print("micro_live_allowed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("next=TOP3_RUNTIME_APPROVAL_BOARD_V1")
    print("VERDICT=TOP3_SHADOW_RUNTIME_REPORT_V1_READY")


if __name__ == "__main__":
    main()
