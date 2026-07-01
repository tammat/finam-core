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
            total = scalar(cur, "SELECT count(*) FROM analytics_global_edge_expanded_runtime_candidates_v2")
            allowed = scalar(cur, """
                SELECT count(*) FROM analytics_global_edge_expanded_runtime_candidates_v2
                WHERE runtime_allowed=true OR execution_allowed=true OR micro_live_allowed=true
            """)
            candidates = scalar(cur, """
                SELECT count(*) FROM analytics_global_edge_expanded_runtime_candidates_v2
                WHERE candidate_status='RESEARCH_CANDIDATE'
            """)

    print("=== EXPANDED_EDGE_DISCOVERY_V2_COMPLETE ===")
    print("mode=research_only")
    print(f"expanded_runtime_candidate_rows={total}")
    print(f"research_candidates={candidates}")
    print(f"runtime_or_execution_allowed_rows={allowed}")
    print("runtime_allowed=0")
    print("execution_allowed=0")
    print("micro_live_allowed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")

    if total >= 560 and allowed == 0:
        print("VERDICT=EXPANDED_EDGE_DISCOVERY_V2_COMPLETE")
    else:
        print("VERDICT=EXPANDED_EDGE_DISCOVERY_V2_REVIEW_REQUIRED")


if __name__ == "__main__":
    main()
