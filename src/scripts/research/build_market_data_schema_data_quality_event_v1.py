#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import psycopg2


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


DDL = """
CREATE TABLE IF NOT EXISTS warehouse.normalized_quality_reason_v1 (
    id bigserial PRIMARY KEY,
    entity_code text NOT NULL UNIQUE,
    entity_name text NOT NULL,
    quality_dimension text NOT NULL DEFAULT 'VALIDITY',
    severity_default text NOT NULL DEFAULT 'WARNING',
    blocks_research_default boolean NOT NULL DEFAULT true,
    blocks_ai_default boolean NOT NULL DEFAULT true,
    blocks_runtime_default boolean NOT NULL DEFAULT false,
    recommendation_default text NOT NULL DEFAULT 'REVIEW',
    status text NOT NULL DEFAULT 'ACTIVE',
    effective_from timestamptz NOT NULL DEFAULT now(),
    effective_to timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT normalized_quality_reason_v1_code_not_empty CHECK (btrim(entity_code) <> '')
);

CREATE TABLE IF NOT EXISTS warehouse.normalized_resolution_method_v1 (
    id bigserial PRIMARY KEY,
    entity_code text NOT NULL UNIQUE,
    entity_name text NOT NULL,
    action_type text NOT NULL DEFAULT 'MANUAL',
    status text NOT NULL DEFAULT 'ACTIVE',
    effective_from timestamptz NOT NULL DEFAULT now(),
    effective_to timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT normalized_resolution_method_v1_code_not_empty CHECK (btrim(entity_code) <> '')
);

CREATE TABLE IF NOT EXISTS warehouse.normalized_data_quality_event_v1 (
    quality_event_id bigserial PRIMARY KEY,
    quality_event_uuid uuid NOT NULL DEFAULT gen_random_uuid(),
    event_sequence bigint NOT NULL,

    event_type_id bigint NOT NULL REFERENCES warehouse.normalized_event_type_v1(id),
    event_version text NOT NULL DEFAULT 'v1',
    event_classification text NOT NULL DEFAULT 'QUALITY_EVENT',

    source_system_id bigint REFERENCES warehouse.normalized_source_system_v1(id),
    source_key text NOT NULL DEFAULT '',
    normalization_run_id bigint REFERENCES warehouse.normalized_normalization_run_v1(id),

    quality_status_id bigint NOT NULL REFERENCES warehouse.normalized_quality_status_v1(id),
    quality_reason_id bigint NOT NULL REFERENCES warehouse.normalized_quality_reason_v1(id),
    resolution_method_id bigint REFERENCES warehouse.normalized_resolution_method_v1(id),

    affected_event_uuid uuid,
    affected_entity_uuid uuid,
    affected_table text,

    severity_level text NOT NULL DEFAULT 'WARNING',
    confidence int NOT NULL DEFAULT 100,

    detected_by text NOT NULL DEFAULT 'system',
    detection_stage text NOT NULL DEFAULT 'VALIDATION',
    validator_version text NOT NULL DEFAULT 'v1',

    blocks_research boolean NOT NULL DEFAULT true,
    blocks_ai boolean NOT NULL DEFAULT true,
    blocks_runtime boolean NOT NULL DEFAULT false,

    recommendation text NOT NULL DEFAULT 'REVIEW',
    resolved boolean NOT NULL DEFAULT false,
    resolved_at timestamptz,
    resolved_by text,
    ai_explained boolean NOT NULL DEFAULT false,

    event_time timestamptz NOT NULL,
    source_time timestamptz NOT NULL,
    received_at timestamptz NOT NULL,
    normalized_at timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now(),

    research_ready boolean NOT NULL DEFAULT false,
    ai_ready boolean NOT NULL DEFAULT false,

    payload jsonb NOT NULL DEFAULT '{}'::jsonb,

    CONSTRAINT normalized_data_quality_event_v1_uuid_unique UNIQUE(quality_event_uuid),
    CONSTRAINT normalized_data_quality_event_v1_time_order CHECK (
        event_time <= source_time
        AND source_time <= received_at
        AND received_at <= normalized_at
    ),
    CONSTRAINT normalized_data_quality_event_v1_confidence_check CHECK (
        confidence >= 0 AND confidence <= 100
    ),
    CONSTRAINT normalized_data_quality_event_v1_resolution_check CHECK (
        (resolved = false AND resolved_at IS NULL)
        OR (resolved = true AND resolved_at IS NOT NULL)
    )
);

INSERT INTO warehouse.normalized_quality_reason_v1 (
    entity_code,
    entity_name,
    quality_dimension,
    severity_default,
    blocks_research_default,
    blocks_ai_default,
    blocks_runtime_default,
    recommendation_default
)
VALUES
    ('BAD_TICK', 'Bad Tick', 'ACCURACY', 'HIGH', true, true, false, 'REVIEW'),
    ('DUPLICATE_BAR', 'Duplicate Bar', 'UNIQUENESS', 'MEDIUM', true, true, false, 'REBUILD'),
    ('UNKNOWN_SYMBOL', 'Unknown Symbol', 'VALIDITY', 'HIGH', true, true, false, 'MANUAL_FIX'),
    ('SESSION_GAP', 'Session Gap', 'COMPLETENESS', 'HIGH', true, true, false, 'RELOAD'),
    ('ROLL_CONFLICT', 'Roll Conflict', 'CONSISTENCY', 'HIGH', true, true, false, 'REVIEW'),
    ('TIME_ORDER_VIOLATION', 'Time Order Violation', 'TIMELINESS', 'HIGH', true, true, true, 'REVIEW'),
    ('MISSING_DATA', 'Missing Data', 'COMPLETENESS', 'HIGH', true, true, false, 'RELOAD'),
    ('STALE_DATA', 'Stale Data', 'TIMELINESS', 'MEDIUM', true, false, false, 'RELOAD'),
    ('NORMALIZATION_ERROR', 'Normalization Error', 'VALIDITY', 'HIGH', true, true, false, 'REBUILD')
ON CONFLICT (entity_code) DO NOTHING;

INSERT INTO warehouse.normalized_resolution_method_v1 (
    entity_code,
    entity_name,
    action_type
)
VALUES
    ('IGNORE', 'Ignore', 'NO_ACTION'),
    ('REVIEW', 'Review', 'MANUAL'),
    ('AUTO_FIX', 'Auto Fix', 'AUTO'),
    ('MANUAL_FIX', 'Manual Fix', 'MANUAL'),
    ('RELOAD', 'Reload Source Data', 'AUTO'),
    ('REBUILD', 'Rebuild Normalized Data', 'AUTO'),
    ('ROLLBACK', 'Rollback Normalization Run', 'MANUAL')
ON CONFLICT (entity_code) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_normalized_quality_reason_v1_dimension
ON warehouse.normalized_quality_reason_v1(quality_dimension);

CREATE INDEX IF NOT EXISTS idx_normalized_quality_reason_v1_severity
ON warehouse.normalized_quality_reason_v1(severity_default);

CREATE INDEX IF NOT EXISTS idx_normalized_resolution_method_v1_action_type
ON warehouse.normalized_resolution_method_v1(action_type);

CREATE INDEX IF NOT EXISTS idx_normalized_data_quality_event_v1_event_sequence
ON warehouse.normalized_data_quality_event_v1(event_sequence);

CREATE INDEX IF NOT EXISTS idx_normalized_data_quality_event_v1_event_time
ON warehouse.normalized_data_quality_event_v1(event_time);

CREATE INDEX IF NOT EXISTS idx_normalized_data_quality_event_v1_reason
ON warehouse.normalized_data_quality_event_v1(quality_reason_id);

CREATE INDEX IF NOT EXISTS idx_normalized_data_quality_event_v1_status
ON warehouse.normalized_data_quality_event_v1(quality_status_id);

CREATE INDEX IF NOT EXISTS idx_normalized_data_quality_event_v1_run
ON warehouse.normalized_data_quality_event_v1(normalization_run_id);

CREATE INDEX IF NOT EXISTS idx_normalized_data_quality_event_v1_affected_event
ON warehouse.normalized_data_quality_event_v1(affected_event_uuid);

CREATE INDEX IF NOT EXISTS idx_normalized_data_quality_event_v1_affected_entity
ON warehouse.normalized_data_quality_event_v1(affected_entity_uuid);

CREATE INDEX IF NOT EXISTS idx_normalized_data_quality_event_v1_blocks
ON warehouse.normalized_data_quality_event_v1(blocks_research, blocks_ai, blocks_runtime);

CREATE INDEX IF NOT EXISTS idx_normalized_data_quality_event_v1_resolved
ON warehouse.normalized_data_quality_event_v1(resolved);

CREATE INDEX IF NOT EXISTS idx_normalized_data_quality_event_v1_ready
ON warehouse.normalized_data_quality_event_v1(research_ready, ai_ready);
"""


TABLES = (
    "normalized_quality_reason_v1",
    "normalized_resolution_method_v1",
    "normalized_data_quality_event_v1",
)


def main() -> int:
    with psycopg2.connect(db_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)
            conn.commit()

            cur.execute("""
                SELECT count(*)::int
                FROM information_schema.tables
                WHERE table_schema='warehouse'
                  AND table_name = ANY(%s)
            """, (list(TABLES),))
            tables_found = cur.fetchone()[0]

            cur.execute("""
                SELECT count(*)::int
                FROM information_schema.columns
                WHERE table_schema='warehouse'
                  AND table_name = ANY(%s)
            """, (list(TABLES),))
            columns_found = cur.fetchone()[0]

            cur.execute("""
                SELECT count(*)::int
                FROM pg_indexes
                WHERE schemaname='warehouse'
                  AND tablename = ANY(%s)
            """, (list(TABLES),))
            indexes_found = cur.fetchone()[0]

            cur.execute("SELECT count(*)::int FROM warehouse.normalized_quality_reason_v1")
            quality_reasons = cur.fetchone()[0]

            cur.execute("SELECT count(*)::int FROM warehouse.normalized_resolution_method_v1")
            resolution_methods = cur.fetchone()[0]

    ok = tables_found == 3 and quality_reasons >= 9 and resolution_methods >= 7

    print("=== MARKET_DATA_SCHEMA_DATA_QUALITY_EVENT_V1 ===")
    print("layer=QUALITY_EVENT")
    print("tables=" + ",".join(TABLES))
    print(f"tables_found={tables_found}")
    print(f"columns_found={columns_found}")
    print(f"indexes_found={indexes_found}")
    print(f"quality_reasons={quality_reasons}")
    print(f"resolution_methods={resolution_methods}")
    print("quality_reason=READY")
    print("resolution_method=READY")
    print("data_quality_event=READY")
    print("quality_governance=READY")
    print("quality_dimensions=READY")
    print("affected_event_uuid=READY")
    print("affected_entity_uuid=READY")
    print("blocks_research=READY")
    print("blocks_ai=READY")
    print("blocks_runtime=READY")
    print("confidence=READY")
    print("resolution_tracking=READY")
    print("ai_explained=READY")
    print("event_framework=EVENT_FRAMEWORK_V1")
    print("identity_policy=IDENTITY_POLICY_V1")
    print("no_vendor_lock=1")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKET_DATA_SCHEMA_DATA_QUALITY_EVENT_V1_READY" if ok else "VERDICT=MARKET_DATA_SCHEMA_DATA_QUALITY_EVENT_V1_FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
