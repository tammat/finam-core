#!/usr/bin/env python3

import os
import psycopg2


def main() -> int:
    print("=== GLOBAL_EDGE_SCORECARD_PERSISTENCE_VALIDATION_V1 ===")
    print("mode=validation_read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("orders_sent=0")

    db = os.environ.get("DATABASE_URL", "")
    if not db:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2
    if db.startswith("sqlite"):
        print("ERROR=SQLITE_FORBIDDEN")
        return 2

    with psycopg2.connect(db) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT run_id, rows_total, positive_rows, research_candidates, micro_live_candidates
                FROM research.analytics_global_edge_scorecard_runs_v1
                ORDER BY run_id DESC
                LIMIT 1;
            """)
            run = cur.fetchone()

            if not run:
                print("VERDICT=GLOBAL_EDGE_SCORECARD_PERSISTENCE_VALIDATION_NO_RUN")
                return 1

            run_id, rows_total, positive_rows, research_candidates, micro_live_candidates = run

            cur.execute("""
                SELECT
                    COUNT(*) AS rows_inserted,
                    SUM(CASE WHEN status='RESEARCH_CANDIDATE' THEN 1 ELSE 0 END) AS candidate_rows,
                    SUM(CASE WHEN status='POSITIVE_OBSERVATION' THEN 1 ELSE 0 END) AS positive_observation_rows,
                    SUM(CASE WHEN status LIKE 'REJECTED%%' THEN 1 ELSE 0 END) AS rejected_rows
                FROM research.analytics_global_edge_scorecard_v1
                WHERE run_id=%s;
            """, (run_id,))
            rows_inserted, candidate_rows, positive_observation_rows, rejected_rows = cur.fetchone()

            cur.execute("""
                SELECT COUNT(*)
                FROM research.analytics_global_edge_scorecard_v1
                WHERE run_id=%s
                  AND payload IS NOT NULL;
            """, (run_id,))
            payload_rows = cur.fetchone()[0]

    print("")
    print("SUMMARY")
    print(f"run_id={run_id}")
    print(f"run_rows_total={rows_total}")
    print(f"run_positive_rows={positive_rows}")
    print(f"run_research_candidates={research_candidates}")
    print(f"run_micro_live_candidates={micro_live_candidates}")
    print(f"rows_inserted={rows_inserted}")
    print(f"candidate_rows={candidate_rows}")
    print(f"positive_observation_rows={positive_observation_rows}")
    print(f"rejected_rows={rejected_rows}")
    print(f"payload_rows={payload_rows}")

    verdict = "GLOBAL_EDGE_SCORECARD_PERSISTENCE_VALIDATION_OK"

    if rows_inserted != rows_total:
        verdict = "GLOBAL_EDGE_SCORECARD_PERSISTENCE_VALIDATION_ROW_MISMATCH"
    elif candidate_rows != research_candidates:
        verdict = "GLOBAL_EDGE_SCORECARD_PERSISTENCE_VALIDATION_CANDIDATE_MISMATCH"
    elif payload_rows != rows_inserted:
        verdict = "GLOBAL_EDGE_SCORECARD_PERSISTENCE_VALIDATION_PAYLOAD_MISSING"

    print("")
    print(f"VERDICT={verdict}")
    return 0 if verdict == "GLOBAL_EDGE_SCORECARD_PERSISTENCE_VALIDATION_OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
