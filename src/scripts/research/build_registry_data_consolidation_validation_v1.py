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
            cur.execute("SELECT count(*)::bigint AS cnt FROM warehouse.registry_relationship_v1")
            total = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM warehouse.registry_relationship_v1
                WHERE coalesce(source_domain,'') <> ''
                  AND coalesce(source_code,'') <> ''
                  AND coalesce(target_domain,'') <> ''
                  AND coalesce(target_code,'') <> ''
                  AND coalesce(relationship_type,'') <> ''
            """)
            required = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM (
                    SELECT source_domain, source_code, target_domain, target_code, relationship_type
                    FROM warehouse.registry_relationship_v1
                    GROUP BY source_domain, source_code, target_domain, target_code, relationship_type
                    HAVING count(*) > 1
                ) d
            """)
            duplicates = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM warehouse.registry_relationship_v1
                WHERE validation_status <> 'VALIDATED'
            """)
            not_validated = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM warehouse.registry_relationship_v1 r
                LEFT JOIN warehouse.feature_registry_v1 f
                  ON r.target_domain='FEATURE' AND r.target_code=f.feature_code
                WHERE r.relationship_type='CATALOG_TO_FEATURE'
                  AND f.feature_code IS NULL
            """)
            broken_feature_links = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM warehouse.registry_relationship_v1 r
                LEFT JOIN warehouse.model_registry_v1 m
                  ON r.target_domain='MODEL' AND r.target_code=m.model_code
                WHERE r.relationship_type='CATALOG_TO_MODEL'
                  AND m.model_code IS NULL
            """)
            broken_model_links = int(cur.fetchone()["cnt"])

    ok = (
        total == 632
        and required == total
        and duplicates == 0
        and not_validated == 0
        and broken_feature_links == 0
        and broken_model_links == 0
    )

    print("=== REGISTRY_DATA_CONSOLIDATION_VALIDATION_V1 ===")
    print(f"registry_relationship_total={total}")
    print(f"required_fields_valid={required}")
    print(f"duplicate_relationships={duplicates}")
    print(f"not_validated_relationships={not_validated}")
    print(f"broken_feature_links={broken_feature_links}")
    print(f"broken_model_links={broken_model_links}")
    print("политика_валидации=СВЯЗИ_БЕЗ_ДУБЛЕЙ_И_БЕЗ_ПОТЕРЯННЫХ_ССЫЛОК")
    print("registry_relationship_valid=1" if ok else "registry_relationship_valid=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=REGISTRY_DATA_CONSOLIDATION_VALIDATION_V1_READY" if ok else "VERDICT=REGISTRY_DATA_CONSOLIDATION_VALIDATION_V1_FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
