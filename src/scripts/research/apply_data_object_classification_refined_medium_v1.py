#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

def main() -> None:
    print("=== DATA_OBJECT_CLASSIFICATION_APPLY_REFINED_MEDIUM_V1 ===")

    conn = psycopg2.connect(DB)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT count(*)
                FROM warehouse.data_object_classification_remaining_medium_review_v1
                WHERE active=true
                  AND decision='APPLY';
            """)
            refined_to_apply = cur.fetchone()[0]

            cur.execute("""
                UPDATE warehouse.data_object_classification_v1 c
                SET object_type = r.refined_object_type,
                    updated_at = now()
                FROM warehouse.data_object_classification_remaining_medium_review_v1 r
                WHERE c.schema_name = r.schema_name
                  AND c.table_name = r.table_name
                  AND c.active=true
                  AND r.active=true
                  AND r.decision='APPLY';
            """)
            applied = cur.rowcount

            cur.execute("""
                UPDATE warehouse.data_object_classification_review_v1 rv
                SET review_status='APPLIED_REFINED_MEDIUM',
                    suggested_object_type = rm.refined_object_type,
                    rule_name = rm.refined_rule_name,
                    updated_at=now()
                FROM warehouse.data_object_classification_remaining_medium_review_v1 rm
                WHERE rv.schema_name = rm.schema_name
                  AND rv.table_name = rm.table_name
                  AND rv.active=true
                  AND rm.active=true
                  AND rm.decision='APPLY'
                  AND rv.review_status='SUGGESTED'
                  AND rv.confidence='MEDIUM';
            """)
            review_updated = cur.rowcount

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

        conn.commit()

        print(f"refined_medium_to_apply={refined_to_apply}")
        print(f"classification_rows_updated={applied}")
        print(f"review_rows_updated={review_updated}")
        print(f"other_after={other_after}")
        print(f"medium_remaining={medium_remaining}")
        print(f"low_remaining={low_remaining}")
        print("low_applied=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        if (
            refined_to_apply == 13
            and applied == 13
            and review_updated == 13
            and other_after == 10
            and medium_remaining == 0
            and low_remaining == 10
        ):
            print("VERDICT=DATA_OBJECT_CLASSIFICATION_APPLY_REFINED_MEDIUM_V1_READY")
        else:
            print("VERDICT=DATA_OBJECT_CLASSIFICATION_APPLY_REFINED_MEDIUM_V1_FAILED")
            raise SystemExit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
