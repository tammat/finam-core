from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

DEFAULT_PARAMS = [
    ("lookback", "int", 10, 60, 10),
    ("hold", "int", 3, 20, 3),
    ("threshold", "float", 0.5, 2.5, 0.5),
    ("commission", "float", 0, 0, 0),
    ("slippage", "float", 0, 0, 0),
]

def main() -> None:
    inserted = 0
    jobs = 0

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT strategy_code
                FROM analytics.strategy_library_v1
                WHERE enabled=true
                ORDER BY priority ASC;
            """)
            strategies = cur.fetchall()

            for s in strategies:
                strategy_code = s["strategy_code"]
                for name, typ, mn, mx, step in DEFAULT_PARAMS:
                    cur.execute("""
                        INSERT INTO analytics.parameter_search_space_v1 (
                            strategy_code, parameter_name, parameter_type,
                            min_value, max_value, step_value,
                            search_method, enabled, source_version, updated_at
                        )
                        VALUES (%s,%s,%s,%s,%s,%s,'GRID',true,'PARAMETER_SEARCH_FOUNDATION_V1',now())
                        ON CONFLICT(strategy_code, parameter_name) DO UPDATE SET
                            parameter_type=EXCLUDED.parameter_type,
                            min_value=EXCLUDED.min_value,
                            max_value=EXCLUDED.max_value,
                            step_value=EXCLUDED.step_value,
                            search_method=EXCLUDED.search_method,
                            enabled=true,
                            source_version='PARAMETER_SEARCH_FOUNDATION_V1',
                            updated_at=now();
                    """, (strategy_code, name, typ, mn, mx, step))
                    inserted += 1

            cur.execute("""
                INSERT INTO analytics.parameter_search_job_v1 (
                    search_code, strategy_code, symbol, timeframe,
                    method_code, status_code, max_trials, objective_metric
                )
                SELECT
                    'SEARCH:' || rq.strategy_code || ':' || rq.symbol || ':' || rq.timeframe,
                    rq.strategy_code,
                    rq.symbol,
                    rq.timeframe,
                    'GRID',
                    'QUEUED',
                    100,
                    'normalized_edge_score'
                FROM analytics.research_queue_v1 rq
                ON CONFLICT(search_code) DO NOTHING;
            """)
            jobs = cur.rowcount

            cur.execute("SELECT count(*) AS c FROM analytics.parameter_search_space_v1;")
            spaces = cur.fetchone()["c"]
            cur.execute("SELECT count(*) AS c FROM analytics.parameter_search_job_v1;")
            total_jobs = cur.fetchone()["c"]

    print("=== PARAMETER_SEARCH_FOUNDATION_V1 ===")
    print(f"search_spaces_total={spaces}")
    print(f"search_params_upserted={inserted}")
    print(f"search_jobs_created={jobs}")
    print(f"search_jobs_total={total_jobs}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=PARAMETER_SEARCH_FOUNDATION_V1_READY")

if __name__ == "__main__":
    main()
