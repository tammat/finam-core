#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

def main() -> None:
    print("=== DATA_OBJECT_CLASSIFICATION_APPLY_HIGH_CONFIDENCE_V1 ===")

    conn = psycopg2.connect(DB)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT count(*)
                FROM warehouse.data_object_classification_review_v1
                WHERE active=true
                  AND review_status='SUGGESTED'
                  AND confidence='HIGH'
                  AND suggested_object_type <> current_object_type;
            """)
            high_to_apply = cur.fetchone()[0]

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
                  AND r.confidence='HIGH'
                  AND r.suggested_object_type <> r.current_object_type;
            """)
            applied = cur.rowcount

            cur.execute("""
                UPDATE warehouse.data_object_classification_review_v1
                SET review_status='APPLIED_HIGH',
                    updated_at=now()
                WHERE active=true
                  AND review_status='SUGGESTED'
                  AND confidence='HIGH'
                  AND suggested_object_type <> current_object_type;
            """)

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
                  AND confidence='HIGH';
            """)
            high_remaining = cur.fetchone()[0]

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

        conn.commit()

        print(f"high_confidence_to_apply={high_to_apply}")
        print(f"classification_rows_updated={applied}")
        print(f"other_after={other_after}")
        print(f"high_remaining={high_remaining}")
        print(f"medium_remaining={medium_remaining}")
        print(f"low_remaining={low_remaining}")
        print("medium_applied=0")
        print("low_applied=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")
        print("VERDICT=DATA_OBJECT_CLASSIFICATION_APPLY_HIGH_CONFIDENCE_V1_READY")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
