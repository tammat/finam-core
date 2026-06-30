#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

MATCH_SQL = """
WITH data_objects AS (
    SELECT schema_name, table_name
    FROM warehouse.data_object_classification_v1
    WHERE active=true
      AND object_type='DATA_SOURCE'
),
mapped AS (
    SELECT
        d.schema_name,
        d.table_name,
        CASE
            WHEN d.schema_name='public'
             AND d.table_name IN ('market_bars', 'market_ticks', 'market_data')
            THEN 'Finam Runtime'

            WHEN d.schema_name='warehouse'
             AND d.table_name LIKE 'normalized_%'
            THEN 'Finam History'

            ELSE NULL
        END AS source_origin
    FROM data_objects d
),
scored AS (
    SELECT
        m.schema_name,
        m.table_name,
        m.source_origin,
        r.source_origin IS NOT NULL AS covered
    FROM mapped m
    LEFT JOIN warehouse.data_source_registry_v1 r
      ON r.active=true
     AND r.source_origin=m.source_origin
)
SELECT schema_name, table_name, source_origin, covered
FROM scored
ORDER BY schema_name, table_name;
"""

def main() -> None:
    print("=== DATA_SOURCE_REGISTRY_TRUE_COVERAGE_V1 ===")

    conn = psycopg2.connect(DB)
    try:
        with conn.cursor() as cur:
            cur.execute(MATCH_SQL)
            rows = cur.fetchall()

        total = len(rows)
        covered = 0
        uncovered = 0

        for schema, table, source_origin, is_covered in rows:
            if is_covered:
                covered += 1
                print(
                    f"DATA_SOURCE_COVERED|schema={schema}|table={table}"
                    f"|source_origin={source_origin}"
                )
            else:
                uncovered += 1
                print(
                    f"DATA_SOURCE_UNCOVERED|schema={schema}|table={table}"
                    f"|reason=NO_ACTIVE_SOURCE_REGISTRY_MAPPING"
                )

        coverage_pct = round((covered / total) * 100, 2) if total else 0.0
        gap_pct = round((uncovered / total) * 100, 2) if total else 0.0

        print(f"data_source_objects={total}")
        print(f"covered_data_source_objects={covered}")
        print(f"uncovered_data_source_objects={uncovered}")
        print(f"true_coverage_pct={coverage_pct}")
        print(f"true_gap_pct={gap_pct}")
        print("denominator=DATA_SOURCE_ONLY")
        print("reference_excluded=1")
        print("governance_excluded=1")
        print("workflow_excluded=1")
        print("runtime_state_excluded=1")
        print("telemetry_excluded=1")
        print("registry_excluded=1")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        if total > 0 and covered > 0:
            print("VERDICT=DATA_SOURCE_REGISTRY_TRUE_COVERAGE_V1_READY")
        else:
            print("VERDICT=DATA_SOURCE_REGISTRY_TRUE_COVERAGE_V1_FAILED")
            raise SystemExit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
