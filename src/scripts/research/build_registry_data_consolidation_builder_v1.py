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
                INSERT INTO warehouse.registry_relationship_v1 (
                    source_domain, source_code,
                    target_domain, target_code,
                    relationship_type,
                    relationship_strength,
                    source_of_truth,
                    evidence_level,
                    validation_status,
                    payload,
                    updated_at
                )
                SELECT
                    'CATALOG',
                    c.object_id,
                    'FEATURE',
                    f.feature_code,
                    'CATALOG_TO_FEATURE',
                    1.0,
                    'REGISTRY_DATA_CONSOLIDATION',
                    'DERIVED',
                    'VALIDATED',
                    jsonb_build_object(
                        'rule', 'catalog_object_id_equals_feature_code',
                        'source_catalog_domain', c.domain,
                        'feature_status', f.status,
                        'feature_maturity', f.maturity_level,
                        'runtime_changed', false,
                        'execution_changed', false,
                        'orders_changed', false,
                        'fills_changed', false,
                        'micro_live_allowed', false
                    ),
                    now()
                FROM warehouse.analytics_asset_catalog_v1 c
                JOIN warehouse.feature_registry_v1 f
                  ON f.feature_code = c.object_id
                WHERE c.domain='FEATURES'
                ON CONFLICT(source_domain, source_code, target_domain, target_code, relationship_type)
                DO UPDATE SET
                    relationship_strength=EXCLUDED.relationship_strength,
                    source_of_truth=EXCLUDED.source_of_truth,
                    evidence_level=EXCLUDED.evidence_level,
                    validation_status=EXCLUDED.validation_status,
                    payload=EXCLUDED.payload,
                    updated_at=now()
            """)
            feature_links = cur.rowcount

            cur.execute("""
                INSERT INTO warehouse.registry_relationship_v1 (
                    source_domain, source_code,
                    target_domain, target_code,
                    relationship_type,
                    relationship_strength,
                    source_of_truth,
                    evidence_level,
                    validation_status,
                    payload,
                    updated_at
                )
                SELECT
                    'CATALOG',
                    c.object_id,
                    'MODEL',
                    m.model_code,
                    'CATALOG_TO_MODEL',
                    1.0,
                    'REGISTRY_DATA_CONSOLIDATION',
                    'DERIVED',
                    'VALIDATED',
                    jsonb_build_object(
                        'rule', 'catalog_object_id_equals_model_code',
                        'source_catalog_domain', c.domain,
                        'model_status', m.status,
                        'model_maturity', m.maturity_level,
                        'runtime_changed', false,
                        'execution_changed', false,
                        'orders_changed', false,
                        'fills_changed', false,
                        'micro_live_allowed', false
                    ),
                    now()
                FROM warehouse.analytics_asset_catalog_v1 c
                JOIN warehouse.model_registry_v1 m
                  ON m.model_code = c.object_id
                WHERE c.domain='MODELS'
                ON CONFLICT(source_domain, source_code, target_domain, target_code, relationship_type)
                DO UPDATE SET
                    relationship_strength=EXCLUDED.relationship_strength,
                    source_of_truth=EXCLUDED.source_of_truth,
                    evidence_level=EXCLUDED.evidence_level,
                    validation_status=EXCLUDED.validation_status,
                    payload=EXCLUDED.payload,
                    updated_at=now()
            """)
            model_links = cur.rowcount

            conn.commit()

            cur.execute("""
                SELECT relationship_type, count(*) AS cnt
                FROM warehouse.registry_relationship_v1
                GROUP BY relationship_type
                ORDER BY relationship_type
            """)
            counts = cur.fetchall()

            cur.execute("SELECT count(*)::bigint AS cnt FROM warehouse.registry_relationship_v1")
            total = int(cur.fetchone()["cnt"])

    print("=== REGISTRY_DATA_CONSOLIDATION_BUILDER_V1 ===")
    print(f"catalog_to_feature_changed={feature_links}")
    print(f"catalog_to_model_changed={model_links}")
    print(f"registry_relationship_total={total}")
    for r in counts:
        print(f"relationship_count={r['relationship_type']}:{r['cnt']}")
    print("политика=СВЯЗИ_БЕЗ_КОПИРОВАНИЯ_ДАННЫХ")
    print("связи=CATALOG_TO_FEATURE,CATALOG_TO_MODEL")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=REGISTRY_DATA_CONSOLIDATION_BUILDER_V1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
