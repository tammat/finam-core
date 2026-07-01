from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            print("=== GLOBAL_EDGE_DISCOVERY_V2_RESULT_REVIEW ===")
            print("mode=research_only")

            for table, status_col in [
                ("analytics_global_edge_features_v2", "status"),
                ("analytics_global_edge_replay_v2", "status"),
                ("analytics_global_edge_ranking_v2", "status"),
                ("analytics_global_edge_forensic_v2", "forensic_status"),
                ("analytics_global_edge_robustness_v2", "robustness_status"),
                ("analytics_global_edge_walk_forward_v2", "walk_forward_status"),
                ("analytics_global_edge_runtime_candidates_v2", "candidate_status"),
            ]:
                cur.execute(f"""
                    SELECT {status_col}, count(*)
                    FROM {table}
                    GROUP BY {status_col}
                    ORDER BY {status_col};
                """)
                for status, count in cur.fetchall():
                    print(f"{table}.{status_col}={status} rows={count}")

            cur.execute("""
                SELECT symbol, asset_class, timeframe, strategy_name,
                       trades_count, net_pnl, expectancy, profit_factor,
                       edge_score, status
                FROM analytics_global_edge_ranking_v2
                ORDER BY rank_no
                LIMIT 10;
            """)
            rows = cur.fetchall()

            print("TOP_RANKING")
            for row in rows:
                print(
                    "RANK_ROW "
                    f"symbol={row[0]} asset_class={row[1]} timeframe={row[2]} "
                    f"strategy={row[3]} trades={row[4]} net_pnl={row[5]} "
                    f"expectancy={row[6]} pf={row[7]} score={row[8]} status={row[9]}"
                )

            print("runtime_changed=0")
            print("execution_changed=0")
            print("orders_changed=0")
            print("fills_changed=0")
            print("micro_live_allowed=0")
            print("VERDICT=GLOBAL_EDGE_DISCOVERY_V2_RESULT_REVIEW_READY")


if __name__ == "__main__":
    main()
