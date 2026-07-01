from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    c.symbol,
                    c.asset_class,
                    c.timeframe,
                    c.strategy_family,
                    c.regime,
                    r.trades_count,
                    r.expectancy,
                    r.profit_factor,
                    r.edge_score,
                    c.candidate_status
                FROM analytics_global_edge_expanded_runtime_candidates_v2 c
                JOIN analytics_global_edge_expanded_ranking_v2 r
                  ON r.symbol = c.symbol
                 AND r.timeframe = c.timeframe
                 AND r.strategy_family = c.strategy_family
                 AND r.regime = c.regime
                WHERE c.candidate_status = 'RESEARCH_CANDIDATE'
                  AND c.runtime_allowed = false
                  AND c.execution_allowed = false
                  AND c.micro_live_allowed = false
                ORDER BY r.edge_score DESC, r.trades_count DESC
                LIMIT 20;
            """)
            rows = cur.fetchall()

            cur.execute("""
                SELECT count(*)
                FROM analytics_global_edge_expanded_runtime_candidates_v2
                WHERE candidate_status='RESEARCH_CANDIDATE';
            """)
            total_candidates = int(cur.fetchone()[0] or 0)

            cur.execute("""
                SELECT count(*)
                FROM analytics_global_edge_expanded_runtime_candidates_v2
                WHERE runtime_allowed=true
                   OR execution_allowed=true
                   OR micro_live_allowed=true;
            """)
            allowed = int(cur.fetchone()[0] or 0)

    print("=== EXPANDED_EDGE_CANDIDATE_REVIEW_V1 ===")
    print("mode=research_only")
    print(f"research_candidates={total_candidates}")
    print(f"top_rows={len(rows)}")
    print("runtime_allowed=0")
    print("execution_allowed=0")
    print("micro_live_allowed=0")

    for idx, row in enumerate(rows, start=1):
        print(
            "CANDIDATE_ROW "
            f"rank={idx} symbol={row[0]} asset_class={row[1]} timeframe={row[2]} "
            f"strategy_family={row[3]} regime={row[4]} trades={row[5]} "
            f"expectancy={row[6]} profit_factor={row[7]} edge_score={row[8]} "
            f"status={row[9]}"
        )

    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")

    if total_candidates > 0 and len(rows) > 0 and allowed == 0:
        print("VERDICT=EXPANDED_EDGE_CANDIDATE_REVIEW_V1_READY")
    else:
        print("VERDICT=EXPANDED_EDGE_CANDIDATE_REVIEW_V1_REVIEW_REQUIRED")


if __name__ == "__main__":
    main()
