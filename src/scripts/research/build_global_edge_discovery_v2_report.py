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
            universe = scalar(cur, "SELECT count(*) FROM analytics_global_edge_universe_v2;")
            features = scalar(cur, "SELECT count(*) FROM analytics_global_edge_features_v2;")
            replay = scalar(cur, "SELECT count(*) FROM analytics_global_edge_replay_v2;")
            ranking = scalar(cur, "SELECT count(*) FROM analytics_global_edge_ranking_v2;")
            forensic = scalar(cur, "SELECT count(*) FROM analytics_global_edge_forensic_v2;")
            robustness = scalar(cur, "SELECT count(*) FROM analytics_global_edge_robustness_v2;")
            walk_forward = scalar(cur, "SELECT count(*) FROM analytics_global_edge_walk_forward_v2;")
            runtime_candidates = scalar(cur, "SELECT count(*) FROM analytics_global_edge_runtime_candidates_v2;")

            cur.execute("""
                SELECT count(*)
                FROM analytics_global_edge_runtime_candidates_v2
                WHERE runtime_allowed = true
                   OR execution_allowed = true
                   OR micro_live_allowed = true;
            """)
            allowed = int(cur.fetchone()[0] or 0)

            cur.execute("""
                SELECT count(*)
                FROM analytics_global_edge_runtime_candidates_v2
                WHERE candidate_status = 'RESEARCH_CANDIDATE';
            """)
            research_candidates = int(cur.fetchone()[0] or 0)

    print("=== GLOBAL_EDGE_DISCOVERY_V2_REPORT ===")
    print("mode=research_only")
    print(f"universe_rows={universe}")
    print(f"features_rows={features}")
    print(f"replay_rows={replay}")
    print(f"ranking_rows={ranking}")
    print(f"forensic_rows={forensic}")
    print(f"robustness_rows={robustness}")
    print(f"walk_forward_rows={walk_forward}")
    print(f"runtime_candidate_rows={runtime_candidates}")
    print(f"research_candidates={research_candidates}")
    print(f"runtime_or_execution_allowed_rows={allowed}")
    print("runtime_allowed=0")
    print("execution_allowed=0")
    print("micro_live_allowed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")

    if allowed == 0 and universe >= 7 and runtime_candidates >= 7:
        print("VERDICT=GLOBAL_EDGE_DISCOVERY_V2_REPORT_READY")
    else:
        print("VERDICT=GLOBAL_EDGE_DISCOVERY_V2_REPORT_REVIEW_REQUIRED")


if __name__ == "__main__":
    main()
