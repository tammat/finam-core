#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

SAFE_RULES = (
    "event_infra",
    "exit_event_state",
    "paper_analysis",
)

def main() -> None:
    print("=== DATA_OBJECT_CLASSIFICATION_APPLY_MEDIUM_SAFE_V1 ===")

    conn = psycopg2.connect(DB)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT count(*)
                FROM warehouse.data_object_classification_review_v1
                WHERE active=true
                  AND review_status='SUGGESTED'
                  AND confidence='MEDIUM'
                  AND rule_name = ANY(%s)
                  AND suggested_object_type <> current_object_type;
            """, (list(SAFE_RULES),))
            safe_to_apply = cur.fetchone()[0]

            cur.execute("""
                UPDATE warehouse.data_object_classification_v1 c
                SET object_type = r.suggested_object_type,
                    updated_at = now()
                FROM warehouse.data_object_classification_review_v1 r
                WHERE c.schema_name = r.schema_name
                  AND c.table_name = r.table_name
                  AND c.active=true
                  AND r.active=true
                  AND r.review_status='SUGGESTED'
                  AND r.confidence='MEDIUM'
                  AND r.rule_name = ANY(%s)
                  AND r.suggested_object_type <> r.current_object_type;
            """, (list(SAFE_RULES),))
            applied = cur.rowcount

            cur.execute("""
                UPDATE warehouse.data_object_classification_review_v1
                SET review_status='APPLIED_MEDIUM_SAFE',
                    updated_at=now()
                WHERE active=true
                  AND review_status='SUGGESTED'
                  AND confidence='MEDIUM'
                  AND rule_name = ANY(%s)
                  AND suggested_object_type <> current_object_type;
            """, (list(SAFE_RULES),))

            cur.execute("""
                SELECT count(*)
                FROM warehouse.data_object_classification_v1
                WHERE active=true
                  AND object_type='OTHER';
            """)
            other_after = cur.fetchone()[0]

            cur.execute("""
                SELECT count(*)
                FROM warehouse.data_object_classification_review_v1
                WHERE active=true
                  AND review_status='SUGGESTED'
                  AND confidence='MEDIUM';
            """)
            medium_remaining = cur.fetchone()[0]

            cur.execute("""
                SELECT count(*)
                FROM warehouse.data_object_classification_review_v1
                WHERE active=true
                  AND review_status='SUGGESTED'
                  AND confidence='LOW';
            """)
            low_remaining = cur.fetchone()[0]

            cur.execute("""
                SELECT rule_name, count(*)
                FROM warehouse.data_object_classification_review_v1
                WHERE active=true
                  AND review_status='APPLIED_MEDIUM_SAFE'
                GROUP BY rule_name
                ORDER BY rule_name;
            """)
            applied_rules = cur.fetchall()

        conn.commit()

        for rule_name, count in applied_rules:
            print(f"APPLIED_RULE|rule={rule_name}|count={count}")

        print(f"medium_safe_to_apply={safe_to_apply}")
        print(f"classification_rows_updated={applied}")
        print(f"other_after={other_after}")
        print(f"medium_remaining={medium_remaining}")
        print(f"low_remaining={low_remaining}")
        print("review_medium_unsafe_untouched=1")
        print("low_applied=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        if safe_to_apply == 7 and applied == 7 and other_after == 23 and medium_remaining == 13 and low_remaining == 10:
            print("VERDICT=DATA_OBJECT_CLASSIFICATION_APPLY_MEDIUM_SAFE_V1_READY")
        else:
            print("VERDICT=DATA_OBJECT_CLASSIFICATION_APPLY_MEDIUM_SAFE_V1_FAILED")
            raise SystemExit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
