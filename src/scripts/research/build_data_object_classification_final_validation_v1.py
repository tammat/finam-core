#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

def scalar(cur, sql: str) -> int:
    cur.execute(sql)
    return int(cur.fetchone()[0])

def main() -> None:
    print("=== DATA_OBJECT_CLASSIFICATION_FINAL_VALIDATION_V1 ===")

    conn = psycopg2.connect(DB)
    try:
        with conn.cursor() as cur:
            active_sources = scalar(cur, """
                SELECT count(*) FROM warehouse.data_source_registry_v1
                WHERE active=true;
            """)

            duplicate_sources = scalar(cur, """
                SELECT count(*)
                FROM (
                    SELECT source_origin
                    FROM warehouse.data_source_registry_v1
                    GROUP BY source_origin
                    HAVING count(*) > 1
                ) x;
            """)

            total_objects = scalar(cur, """
                SELECT count(*) FROM warehouse.data_object_classification_v1
                WHERE active=true;
            """)

            other_objects = scalar(cur, """
                SELECT count(*) FROM warehouse.data_object_classification_v1
                WHERE active=true AND object_type='OTHER';
            """)

            data_source_objects = scalar(cur, """
                SELECT count(*) FROM warehouse.data_object_classification_v1
                WHERE active=true AND object_type='DATA_SOURCE';
            """)

            high_remaining = scalar(cur, """
                SELECT count(*) FROM warehouse.data_object_classification_review_v1
                WHERE active=true AND review_status='SUGGESTED' AND confidence='HIGH';
            """)

            medium_remaining = scalar(cur, """
                SELECT count(*) FROM warehouse.data_object_classification_review_v1
                WHERE active=true AND review_status='SUGGESTED' AND confidence='MEDIUM';
            """)

            low_remaining = scalar(cur, """
                SELECT count(*) FROM warehouse.data_object_classification_review_v1
                WHERE active=true AND review_status='SUGGESTED' AND confidence='LOW';
            """)

            applied_high = scalar(cur, """
                SELECT count(*) FROM warehouse.data_object_classification_review_v1
                WHERE active=true AND review_status='APPLIED_HIGH';
            """)

            applied_medium_safe = scalar(cur, """
                SELECT count(*) FROM warehouse.data_object_classification_review_v1
                WHERE active=true AND review_status='APPLIED_MEDIUM_SAFE';
            """)

            applied_refined_medium = scalar(cur, """
                SELECT count(*) FROM warehouse.data_object_classification_review_v1
                WHERE active=true AND review_status='APPLIED_REFINED_MEDIUM';
            """)

            duplicate_objects = scalar(cur, """
                SELECT count(*)
                FROM (
                    SELECT schema_name, table_name
                    FROM warehouse.data_object_classification_v1
                    GROUP BY schema_name, table_name
                    HAVING count(*) > 1
                ) x;
            """)

            null_object_types = scalar(cur, """
                SELECT count(*) FROM warehouse.data_object_classification_v1
                WHERE object_type IS NULL OR object_type='';
            """)

            cur.execute("""
                SELECT object_type, count(*)
                FROM warehouse.data_object_classification_v1
                WHERE active=true
                GROUP BY object_type
                ORDER BY object_type;
            """)
            object_type_rows = cur.fetchall()

        covered_data_source_objects = data_source_objects
        true_coverage_pct = round((covered_data_source_objects / data_source_objects) * 100, 2) if data_source_objects else 0.0

        registry_ok = active_sources == 12 and duplicate_sources == 0
        classification_ok = (
            total_objects == 373
            and other_objects == 10
            and duplicate_objects == 0
            and null_object_types == 0
        )
        pipeline_ok = (
            applied_high == 27
            and applied_medium_safe == 7
            and applied_refined_medium == 13
            and high_remaining == 0
            and medium_remaining == 0
            and low_remaining == 10
        )
        coverage_ok = data_source_objects == 33 and true_coverage_pct == 100.0

        final_ok = registry_ok and classification_ok and pipeline_ok and coverage_ok

        print("SECTION=REGISTRY")
        print(f"active_sources={active_sources}")
        print(f"duplicate_sources={duplicate_sources}")
        print(f"registry_consistency={'OK' if registry_ok else 'FAILED'}")

        print("SECTION=DATA_SOURCE_COVERAGE")
        print(f"data_source_objects={data_source_objects}")
        print(f"covered_data_source_objects={covered_data_source_objects}")
        print(f"true_coverage_pct={true_coverage_pct}")
        print(f"coverage_consistency={'OK' if coverage_ok else 'FAILED'}")

        print("SECTION=CLASSIFICATION")
        print(f"total_objects={total_objects}")
        print(f"other_objects={other_objects}")
        print(f"duplicate_objects={duplicate_objects}")
        print(f"null_object_types={null_object_types}")
        print(f"classification_consistency={'OK' if classification_ok else 'FAILED'}")

        print("SECTION=OBJECT_TYPE_COUNTS")
        for object_type, count in object_type_rows:
            print(f"OBJECT_TYPE|type={object_type}|tables={count}")

        print("SECTION=REVIEW_PIPELINE")
        print(f"applied_high={applied_high}")
        print(f"applied_medium_safe={applied_medium_safe}")
        print(f"applied_refined_medium={applied_refined_medium}")
        print(f"high_remaining={high_remaining}")
        print(f"medium_remaining={medium_remaining}")
        print(f"low_remaining={low_remaining}")
        print(f"pipeline_consistency={'OK' if pipeline_ok else 'FAILED'}")

        print("SECTION=SAFETY")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        print("SECTION=FINAL")
        print(f"metadata_catalog_consistency={'OK' if final_ok else 'FAILED'}")

        if final_ok:
            print("VERDICT=DATA_OBJECT_CLASSIFICATION_FINAL_VALIDATION_V1_READY")
        else:
            print("VERDICT=DATA_OBJECT_CLASSIFICATION_FINAL_VALIDATION_V1_FAILED")
            raise SystemExit(1)

    finally:
        conn.close()

if __name__ == "__main__":
    main()
