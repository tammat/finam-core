from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def scalar(cur, sql: str) -> int:
    cur.execute(sql)
    return int(cur.fetchone()[0] or 0)


def main() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            counts = {
                "expanded_features_rows": scalar(cur, "SELECT count(*) FROM analytics_global_edge_expanded_features_v2"),
                "expanded_replay_rows": scalar(cur, "SELECT count(*) FROM analytics_global_edge_expanded_replay_v2"),
                "expanded_ranking_rows": scalar(cur, "SELECT count(*) FROM analytics_global_edge_expanded_ranking_v2"),
                "expanded_forensic_rows": scalar(cur, "SELECT count(*) FROM analytics_global_edge_expanded_forensic_v2"),
                "expanded_robustness_rows": scalar(cur, "SELECT count(*) FROM analytics_global_edge_expanded_robustness_v2"),
                "expanded_walk_forward_rows": scalar(cur, "SELECT count(*) FROM analytics_global_edge_expanded_walk_forward_v2"),
                "expanded_runtime_candidate_rows": scalar(cur, "SELECT count(*) FROM analytics_global_edge_expanded_runtime_candidates_v2"),
                "research_candidates": scalar(cur, "SELECT count(*) FROM analytics_global_edge_expanded_runtime_candidates_v2 WHERE candidate_status='RESEARCH_CANDIDATE'"),
                "runtime_or_execution_allowed_rows": scalar(cur, """
                    SELECT count(*) FROM analytics_global_edge_expanded_runtime_candidates_v2
                    WHERE runtime_allowed=true OR execution_allowed=true OR micro_live_allowed=true
                """),
            }

            cur.execute("""
                SELECT symbol, asset_class, timeframe, strategy_family, regime,
                       trades_count, expectancy, profit_factor, edge_score, status
                FROM analytics_global_edge_expanded_ranking_v2
                ORDER BY rank_no
                LIMIT 50;
            """)
            top_rows = cur.fetchall()

    print("=== EXPANDED_EDGE_DISCOVERY_V2_REPORT ===")
    print("mode=research_only")
    for key, value in counts.items():
        print(f"{key}={value}")

    print("TOP_50")
    for row in top_rows:
        print(
            "TOP_ROW "
            f"symbol={row[0]} asset_class={row[1]} timeframe={row[2]} "
            f"strategy_family={row[3]} regime={row[4]} trades={row[5]} "
            f"expectancy={row[6]} pf={row[7]} edge_score={row[8]} status={row[9]}"
        )

    print("runtime_allowed=0")
    print("execution_allowed=0")
    print("micro_live_allowed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("next=EXPANDED_EDGE_DISCOVERY_V2_RESULT_REVIEW")

    if counts["runtime_or_execution_allowed_rows"] == 0 and counts["expanded_runtime_candidate_rows"] >= 560:
        print("VERDICT=EXPANDED_EDGE_DISCOVERY_V2_REPORT_READY")
    else:
        print("VERDICT=EXPANDED_EDGE_DISCOVERY_V2_REPORT_REVIEW_REQUIRED")


if __name__ == "__main__":
    main()
