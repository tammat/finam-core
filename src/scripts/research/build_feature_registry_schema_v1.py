#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import psycopg2


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


DDL = """
CREATE TABLE IF NOT EXISTS warehouse.feature_registry_v1 (
    feature_id BIGSERIAL PRIMARY KEY,

    feature_code TEXT NOT NULL UNIQUE,
    feature_name TEXT NOT NULL,
    feature_group TEXT,
    feature_class TEXT,

    description TEXT,
    source_of_truth TEXT,
    calculation_builder TEXT,

    input_objects JSONB DEFAULT '[]'::jsonb,
    output_objects JSONB DEFAULT '[]'::jsonb,
    parameters JSONB DEFAULT '{}'::jsonb,

    parameter_version TEXT,
    feature_version TEXT DEFAULT 'v1',

    owner TEXT DEFAULT 'Research',
    status TEXT DEFAULT 'DISCOVERED',
    maturity_level TEXT DEFAULT 'RESEARCH',

    validation_status TEXT DEFAULT 'NOT_VALIDATED',
    research_status TEXT DEFAULT 'AVAILABLE',
    shadow_status TEXT DEFAULT 'NOT_ALLOWED',
    paper_status TEXT DEFAULT 'NOT_ALLOWED',
    live_status TEXT DEFAULT 'NOT_ALLOWED',

    approved_for_research BOOLEAN DEFAULT true,
    approved_for_shadow BOOLEAN DEFAULT false,
    approved_for_paper BOOLEAN DEFAULT false,
    approved_for_live BOOLEAN DEFAULT false,

    quality_score NUMERIC,
    stability_score NUMERIC,
    drift_score NUMERIC,

    last_validation_at TIMESTAMPTZ,

    payload JSONB DEFAULT '{}'::jsonb,

    registry_version TEXT DEFAULT 'FEATURE_REGISTRY_V1',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_feature_registry_status_v1
ON warehouse.feature_registry_v1(status);

CREATE INDEX IF NOT EXISTS idx_feature_registry_maturity_v1
ON warehouse.feature_registry_v1(maturity_level);

CREATE INDEX IF NOT EXISTS idx_feature_registry_class_v1
ON warehouse.feature_registry_v1(feature_class);

CREATE INDEX IF NOT EXISTS idx_feature_registry_group_v1
ON warehouse.feature_registry_v1(feature_group);
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
                  AND table_name='feature_registry_v1'
            """)
            columns = cur.fetchone()[0]

            cur.execute("""
                SELECT count(*)::int
                FROM pg_indexes
                WHERE schemaname='warehouse'
                  AND tablename='feature_registry_v1'
            """)
            indexes = cur.fetchone()[0]

    print("=== FEATURE_REGISTRY_SCHEMA_V1 ===")
    print("table=warehouse.feature_registry_v1")
    print(f"columns={columns}")
    print(f"indexes={indexes}")
    print("status_model=DISCOVERED,REGISTERED,VALIDATED,APPROVED,DEPRECATED,ARCHIVED")
    print("maturity_model=RESEARCH,VALIDATED,SHADOW,PAPER,LIVE")
    print("source_policy=DISCOVERY_TO_REGISTRY")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=FEATURE_REGISTRY_SCHEMA_V1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
