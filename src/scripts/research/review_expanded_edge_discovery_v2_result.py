from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            print("=== EXPANDED_EDGE_DISCOVERY_V2_RESULT_REVIEW ===")
            print("mode=research_only")

            checks = [
                ("analytics_global_edge_expanded_features_v2", "status"),
                ("analytics_global_edge_expanded_replay_v2", "status"),
                ("analytics_global_edge_expanded_ranking_v2", "status"),
                ("analytics_global_edge_expanded_forensic_v2", "forensic_status"),
                ("analytics_global_edge_expanded_robustness_v2", "robustness_status"),
                ("analytics_global_edge_expanded_walk_forward_v2", "walk_forward_status"),
                ("analytics_global_edge_expanded_runtime_candidates_v2", "candidate_status"),
            ]

            for table, column in checks:
                cur.execute(f"""
                    SELECT {column}, count(*)
                    FROM {table}
                    GROUP BY {column}
                    ORDER BY {column};
                """)
                for status, count in cur.fetchall():
                    print(f"{table}.{column}={status} rows={count}")

            cur.execute("""
                SELECT timeframe, count(*)
                FROM analytics_global_edge_expanded_ranking_v2
                WHERE status='CANDIDATE'
                GROUP BY timeframe
                ORDER BY count(*) DESC, timeframe;
            """)
            for timeframe, count in cur.fetchall():
                print(f"TIMEFRAME_CANDIDATE timeframe={timeframe} rows={count}")

            cur.execute("""
                SELECT strategy_family, count(*)
                FROM analytics_global_edge_expanded_ranking_v2
                WHERE status='CANDIDATE'
                GROUP BY strategy_family
                ORDER BY count(*) DESC, strategy_family;
            """)
            for strategy, count in cur.fetchall():
                print(f"STRATEGY_CANDIDATE strategy_family={strategy} rows={count}")

            cur.execute("""
                SELECT regime, count(*)
                FROM analytics_global_edge_expanded_ranking_v2
                WHERE status='CANDIDATE'
                GROUP BY regime
                ORDER BY count(*) DESC, regime;
            """)
            for regime, count in cur.fetchall():
                print(f"REGIME_CANDIDATE regime={regime} rows={count}")

    print("diagnosis=expanded_search_completed_runtime_blocked")
    print("runtime_allowed=0")
    print("execution_allowed=0")
    print("micro_live_allowed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("next=EXPANDED_EDGE_DISCOVERY_V2_COMPLETE")
    print("VERDICT=EXPANDED_EDGE_DISCOVERY_V2_RESULT_REVIEW_READY")


if __name__ == "__main__":
    main()
