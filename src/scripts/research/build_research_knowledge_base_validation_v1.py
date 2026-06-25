#!/usr/bin/env python3

import os
import psycopg2


def scalar(cur, sql, params=()):
    cur.execute(sql, params)
    row = cur.fetchone()
    return row[0] if row else None


def main() -> int:
    print("=== RESEARCH_KNOWLEDGE_BASE_VALIDATION_V1 ===")
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
            candidates = scalar(cur, "SELECT COUNT(*) FROM research.research_candidates_v1;")
            decisions = scalar(cur, "SELECT COUNT(*) FROM research.research_candidate_decisions_v1;")
            hypotheses = scalar(cur, "SELECT COUNT(*) FROM research.research_hypotheses_v1;")
            events = scalar(cur, "SELECT COUNT(*) FROM research.research_knowledge_events_v1;")

            msc_exists = scalar(
                cur,
                """
                SELECT COUNT(*)
                FROM research.research_candidates_v1
                WHERE candidate_id='MSC-000001'
                  AND status='REJECTED'
                  AND status_reason='ROBUSTNESS_WEAK';
                """,
            )

            msc_decisions = scalar(
                cur,
                """
                SELECT COUNT(*)
                FROM research.research_candidate_decisions_v1
                WHERE candidate_id='MSC-000001'
                  AND new_status='REJECTED'
                  AND decision_reason='ROBUSTNESS_WEAK';
                """,
            )

            msc_hypothesis = scalar(
                cur,
                """
                SELECT COUNT(*)
                FROM research.research_hypotheses_v1
                WHERE linked_candidate_id='MSC-000001'
                  AND status='REJECTED'
                  AND status_reason='ROBUSTNESS_WEAK';
                """,
            )

            msc_events = scalar(
                cur,
                """
                SELECT COUNT(*)
                FROM research.research_knowledge_events_v1
                WHERE object_id='MSC-000001'
                  AND event_type='CANDIDATE_REJECTED';
                """,
            )

            duplicate_candidates = scalar(
                cur,
                """
                SELECT COUNT(*)
                FROM (
                    SELECT candidate_id, COUNT(*)
                    FROM research.research_candidates_v1
                    GROUP BY candidate_id
                    HAVING COUNT(*) > 1
                ) q;
                """,
            )

    print("")
    print("SUMMARY")
    print(f"candidates={candidates}")
    print(f"decisions={decisions}")
    print(f"hypotheses={hypotheses}")
    print(f"knowledge_events={events}")
    print(f"msc000001_exists={msc_exists}")
    print(f"msc000001_decisions={msc_decisions}")
    print(f"msc000001_hypothesis={msc_hypothesis}")
    print(f"msc000001_events={msc_events}")
    print(f"duplicate_candidates={duplicate_candidates}")

    verdict = "RESEARCH_KNOWLEDGE_BASE_VALIDATION_OK"
    if not msc_exists:
        verdict = "RESEARCH_KNOWLEDGE_BASE_VALIDATION_MSC000001_MISSING"
    elif not msc_decisions:
        verdict = "RESEARCH_KNOWLEDGE_BASE_VALIDATION_DECISION_MISSING"
    elif not msc_hypothesis:
        verdict = "RESEARCH_KNOWLEDGE_BASE_VALIDATION_HYPOTHESIS_MISSING"
    elif not msc_events:
        verdict = "RESEARCH_KNOWLEDGE_BASE_VALIDATION_EVENT_MISSING"
    elif duplicate_candidates:
        verdict = "RESEARCH_KNOWLEDGE_BASE_VALIDATION_DUPLICATES"

    print("")
    print(f"VERDICT={verdict}")
    return 0 if verdict == "RESEARCH_KNOWLEDGE_BASE_VALIDATION_OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
