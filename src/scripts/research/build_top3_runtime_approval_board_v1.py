from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS analytics_global_edge_top3_runtime_approval_board_v1 (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    rank_no BIGINT NOT NULL,
                    symbol TEXT NOT NULL,
                    asset_class TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    strategy_family TEXT NOT NULL,
                    regime TEXT NOT NULL,
                    shadow_recommendation TEXT NOT NULL,
                    board_decision TEXT NOT NULL,
                    board_reason TEXT NOT NULL,
                    next_stage TEXT NOT NULL,
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
                    recommendation,
                    report_status,
                    risk_status
                FROM analytics_global_edge_top3_shadow_runtime_report_v1
                ORDER BY rank_no
                LIMIT 3;
            """)
            rows = cur.fetchall()

            saved = 0
            paper_approved = 0
            rejected = 0

            print("=== TOP3_RUNTIME_APPROVAL_BOARD_V1 ===")
            print("mode=approval_only")

            for row in rows:
                (
                    rank_no,
                    symbol,
                    asset_class,
                    timeframe,
                    strategy_family,
                    regime,
                    recommendation,
                    report_status,
                    risk_status,
                ) = row

                if recommendation == "GO_PAPER" and report_status == "SHADOW_PASS" and risk_status == "RISK_OK":
                    board_decision = "APPROVE_PAPER"
                    board_reason = "shadow_pass_risk_ok"
                    next_stage = "TOP3_PAPER_RUNTIME_EXECUTION_V1"
                    paper_approved += 1
                else:
                    board_decision = "REJECT_OR_KEEP_SHADOW"
                    board_reason = "shadow_not_confirmed_or_risk_not_ok"
                    next_stage = "RESEARCH_REVIEW"
                    rejected += 1

                cur.execute("""
                    INSERT INTO analytics_global_edge_top3_runtime_approval_board_v1
                    (
                        rank_no,
                        symbol,
                        asset_class,
                        timeframe,
                        strategy_family,
                        regime,
                        shadow_recommendation,
                        board_decision,
                        board_reason,
                        next_stage,
                        runtime_allowed,
                        execution_allowed,
                        micro_live_allowed
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,false,false,false)
                    ON CONFLICT (symbol, timeframe, strategy_family, regime)
                    DO UPDATE SET
                        created_at = now(),
                        rank_no = EXCLUDED.rank_no,
                        asset_class = EXCLUDED.asset_class,
                        shadow_recommendation = EXCLUDED.shadow_recommendation,
                        board_decision = EXCLUDED.board_decision,
                        board_reason = EXCLUDED.board_reason,
                        next_stage = EXCLUDED.next_stage,
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
                    recommendation,
                    board_decision,
                    board_reason,
                    next_stage,
                ))
                saved += 1

                print(
                    "APPROVAL_ROW "
                    f"rank_no={rank_no} symbol={symbol} asset_class={asset_class} "
                    f"timeframe={timeframe} strategy_family={strategy_family} regime={regime} "
                    f"shadow_recommendation={recommendation} board_decision={board_decision} "
                    f"board_reason={board_reason} next_stage={next_stage}"
                )

    print(f"approval_rows={saved}")
    print(f"paper_approved={paper_approved}")
    print(f"rejected_or_keep_shadow={rejected}")
    print("runtime_allowed=0")
    print("execution_allowed=0")
    print("micro_live_allowed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("next=TOP3_PAPER_RUNTIME_EXECUTION_V1")
    print("VERDICT=TOP3_RUNTIME_APPROVAL_BOARD_V1_READY")


if __name__ == "__main__":
    main()
