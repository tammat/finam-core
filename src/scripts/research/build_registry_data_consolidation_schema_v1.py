#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import psycopg2


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


DDL = """
CREATE TABLE IF NOT EXISTS warehouse.registry_relationship_v1 (
    relationship_id BIGSERIAL PRIMARY KEY,

    source_domain TEXT NOT NULL,
    source_code TEXT NOT NULL,

    target_domain TEXT NOT NULL,
    target_code TEXT NOT NULL,

    relationship_type TEXT NOT NULL,
    relationship_strength NUMERIC DEFAULT 1.0,

    source_of_truth TEXT DEFAULT 'REGISTRY_DATA_CONSOLIDATION',
    evidence_level TEXT DEFAULT 'DERIVED',
    validation_status TEXT DEFAULT 'NOT_VALIDATED',

    payload JSONB DEFAULT '{}'::jsonb,

    registry_version TEXT DEFAULT 'REGISTRY_DATA_CONSOLIDATION_V1',

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),

    UNIQUE(source_domain, source_code, target_domain, target_code, relationship_type)
);

CREATE INDEX IF NOT EXISTS idx_registry_relationship_source_v1
ON warehouse.registry_relationship_v1(source_domain, source_code);

CREATE INDEX IF NOT EXISTS idx_registry_relationship_target_v1
ON warehouse.registry_relationship_v1(target_domain, target_code);

CREATE INDEX IF NOT EXISTS idx_registry_relationship_type_v1
ON warehouse.registry_relationship_v1(relationship_type);

CREATE INDEX IF NOT EXISTS idx_registry_relationship_validation_v1
ON warehouse.registry_relationship_v1(validation_status);
"""


def main() -> int:
    with psycopg2.connect(db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)
            conn.commit()

            cur.execute("""
                SELECT count(*)::int
                FROM information_schema.columns
                WHERE table_schema='warehouse'
                  AND table_name='registry_relationship_v1'
            """)
            columns = cur.fetchone()[0]

            cur.execute("""
                SELECT count(*)::int
                FROM pg_indexes
                WHERE schemaname='warehouse'
                  AND tablename='registry_relationship_v1'
            """)
            indexes = cur.fetchone()[0]

    print("=== REGISTRY_DATA_CONSOLIDATION_SCHEMA_V1 ===")
    print("таблица=warehouse.registry_relationship_v1")
    print(f"колонок={columns}")
    print(f"индексов={indexes}")
    print("назначение=единый_слой_связей_registry")
    print("типы_связей=CATALOG_TO_FEATURE,CATALOG_TO_MODEL,FEATURE_TO_EXPERIMENT,EXPERIMENT_TO_MODEL")
    print("политика=СВЯЗИ_БЕЗ_КОПИРОВАНИЯ_ДАННЫХ")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=REGISTRY_DATA_CONSOLIDATION_SCHEMA_V1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
