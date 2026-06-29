#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import psycopg2
import psycopg2.extras


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> int:
    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO warehouse.feature_registry_v1 (
                    feature_code, feature_name, feature_group, feature_class,
                    description, source_of_truth, calculation_builder,
                    input_objects, output_objects, parameters,
                    parameter_version, feature_version,
                    owner, status, maturity_level,
                    validation_status, research_status, shadow_status, paper_status, live_status,
                    approved_for_research, approved_for_shadow, approved_for_paper, approved_for_live,
                    quality_score, stability_score, drift_score,
                    payload, updated_at
                )
                SELECT
                    object_id AS feature_code,
                    object_name AS feature_name,
                    'DISCOVERED_REPOSITORY' AS feature_group,
                    coalesce((payload->'keywords'->>0), 'UNKNOWN') AS feature_class,
                    purpose AS description,
                    source_system AS source_of_truth,
                    payload->>'path' AS calculation_builder,
                    '[]'::jsonb AS input_objects,
                    jsonb_build_array(object_id) AS output_objects,
                    coalesce(payload, '{}'::jsonb) AS parameters,
                    'v1' AS parameter_version,
                    version AS feature_version,
                    owner,
                    'DISCOVERED' AS status,
                    'RESEARCH' AS maturity_level,
                    'NOT_VALIDATED' AS validation_status,
                    'AVAILABLE' AS research_status,
                    'NOT_ALLOWED' AS shadow_status,
                    'NOT_ALLOWED' AS paper_status,
                    'NOT_ALLOWED' AS live_status,
                    true AS approved_for_research,
                    false AS approved_for_shadow,
                    false AS approved_for_paper,
                    false AS approved_for_live,
                    health_score AS quality_score,
                    null::numeric AS stability_score,
                    null::numeric AS drift_score,
                    jsonb_build_object(
                        'source_catalog_object_id', object_id,
                        'source_discovery', payload->>'discovery_source',
                        'registry_builder', 'FEATURE_REGISTRY_BUILDER_V1',
                        'runtime_changed', false,
                        'execution_changed', false,
                        'orders_changed', false,
                        'fills_changed', false,
                        'micro_live_allowed', false
                    ),
                    now()
                FROM warehouse.analytics_asset_catalog_v1
                WHERE domain='FEATURES'
                  AND payload->>'discovery_source'='FeatureDiscovery'
                ON CONFLICT(feature_code) DO UPDATE SET
                    feature_name=EXCLUDED.feature_name,
                    feature_group=EXCLUDED.feature_group,
                    feature_class=EXCLUDED.feature_class,
                    description=EXCLUDED.description,
                    source_of_truth=EXCLUDED.source_of_truth,
                    calculation_builder=EXCLUDED.calculation_builder,
                    parameters=EXCLUDED.parameters,
                    feature_version=EXCLUDED.feature_version,
                    quality_score=EXCLUDED.quality_score,
                    payload=EXCLUDED.payload,
                    updated_at=now()
            """)
            changed = cur.rowcount
            conn.commit()

            cur.execute("SELECT count(*)::bigint AS cnt FROM warehouse.feature_registry_v1")
            total = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT status, count(*) AS cnt
                FROM warehouse.feature_registry_v1
                GROUP BY status
                ORDER BY status
            """)
            statuses = cur.fetchall()

    print("=== FEATURE_REGISTRY_BUILDER_V1 ===")
    print(f"registry_rows_changed={changed}")
    print(f"feature_registry_total={total}")
    for r in statuses:
        print(f"status_count={r['status']}:{r['cnt']}")
    print("source_policy=DISCOVERY_TO_REGISTRY")
    print("registry_version=FEATURE_REGISTRY_V1")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=FEATURE_REGISTRY_BUILDER_V1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
