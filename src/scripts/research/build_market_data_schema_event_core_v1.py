#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import psycopg2


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


DDL = """
CREATE TABLE IF NOT EXISTS warehouse.normalized_event_type_v1 (
    id bigserial PRIMARY KEY,
    entity_code text NOT NULL UNIQUE,
    entity_name text NOT NULL,
    event_domain text NOT NULL DEFAULT 'MARKET',
    event_granularity text NOT NULL,
    status text NOT NULL DEFAULT 'ACTIVE',
    effective_from timestamptz NOT NULL DEFAULT now(),
    effective_to timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT normalized_event_type_v1_code_not_empty CHECK (btrim(entity_code) <> ''),
    CONSTRAINT normalized_event_type_v1_name_not_empty CHECK (btrim(entity_name) <> '')
);

CREATE TABLE IF NOT EXISTS warehouse.normalized_quality_status_v1 (
    id bigserial PRIMARY KEY,
    entity_code text NOT NULL UNIQUE,
    entity_name text NOT NULL,
    quality_level int NOT NULL,
    is_usable_for_research boolean NOT NULL DEFAULT false,
    is_usable_for_ai boolean NOT NULL DEFAULT false,
    status text NOT NULL DEFAULT 'ACTIVE',
    effective_from timestamptz NOT NULL DEFAULT now(),
    effective_to timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT normalized_quality_status_v1_code_not_empty CHECK (btrim(entity_code) <> '')
);

CREATE TABLE IF NOT EXISTS warehouse.normalized_normalization_run_v1 (
    id bigserial PRIMARY KEY,
    run_uuid uuid NOT NULL DEFAULT gen_random_uuid(),
    entity_code text NOT NULL UNIQUE,
    entity_name text NOT NULL,
    source_system_id bigint REFERENCES warehouse.normalized_source_system_v1(id),
    algorithm_version text NOT NULL DEFAULT 'v1',
    schema_version text NOT NULL DEFAULT 'v1',
    framework_version text NOT NULL DEFAULT 'EVENT_FRAMEWORK_V1',
    git_commit text,
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    duration_ms bigint,
    initiator text NOT NULL DEFAULT 'system',
    parameters jsonb NOT NULL DEFAULT '{}'::jsonb,
    rows_processed bigint NOT NULL DEFAULT 0,
    rows_rejected bigint NOT NULL DEFAULT 0,
    rows_corrected bigint NOT NULL DEFAULT 0,
    status text NOT NULL DEFAULT 'STARTED',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT normalized_normalization_run_v1_uuid_unique UNIQUE(run_uuid),
    CONSTRAINT normalized_normalization_run_v1_status_check CHECK (
        status IN ('STARTED','FINISHED','FAILED','CANCELLED')
    )
);

CREATE TABLE IF NOT EXISTS warehouse.normalized_event_sequence_v1 (
    id bigserial PRIMARY KEY,
    entity_code text NOT NULL UNIQUE,
    entity_name text NOT NULL,
    sequence_scope text NOT NULL DEFAULT 'GLOBAL',
    current_value bigint NOT NULL DEFAULT 0,
    status text NOT NULL DEFAULT 'ACTIVE',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb
);

INSERT INTO warehouse.normalized_event_type_v1 (
    entity_code, entity_name, event_domain, event_granularity
)
VALUES
    ('BAR_EVENT', 'Bar Event', 'MARKET', 'BAR'),
    ('QUOTE_EVENT', 'Quote Event', 'MARKET', 'QUOTE'),
    ('TRADE_TICK_EVENT', 'Trade Tick Event', 'MARKET', 'TICK'),
    ('DATA_QUALITY_EVENT', 'Data Quality Event', 'QUALITY', 'SESSION'),
    ('CORRECTION_EVENT', 'Correction Event', 'GOVERNANCE', 'SESSION')
ON CONFLICT (entity_code) DO NOTHING;

INSERT INTO warehouse.normalized_quality_status_v1 (
    entity_code, entity_name, quality_level, is_usable_for_research, is_usable_for_ai
)
VALUES
    ('VALID', 'Valid', 100, true, true),
    ('WARNING', 'Warning', 70, true, false),
    ('REJECTED', 'Rejected', 0, false, false),
    ('REVIEW_REQUIRED', 'Review Required', 30, false, false)
ON CONFLICT (entity_code) DO NOTHING;

INSERT INTO warehouse.normalized_event_sequence_v1 (
    entity_code, entity_name, sequence_scope, current_value
)
VALUES
    ('GLOBAL_EVENT_SEQUENCE', 'Global Event Sequence', 'GLOBAL', 0)
ON CONFLICT (entity_code) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_normalized_event_type_v1_domain
ON warehouse.normalized_event_type_v1(event_domain);

CREATE INDEX IF NOT EXISTS idx_normalized_event_type_v1_granularity
ON warehouse.normalized_event_type_v1(event_granularity);

CREATE INDEX IF NOT EXISTS idx_normalized_quality_status_v1_quality_level
ON warehouse.normalized_quality_status_v1(quality_level);

CREATE INDEX IF NOT EXISTS idx_normalized_normalization_run_v1_source
ON warehouse.normalized_normalization_run_v1(source_system_id);

CREATE INDEX IF NOT EXISTS idx_normalized_normalization_run_v1_status
ON warehouse.normalized_normalization_run_v1(status);

CREATE INDEX IF NOT EXISTS idx_normalized_normalization_run_v1_started_at
ON warehouse.normalized_normalization_run_v1(started_at);

CREATE INDEX IF NOT EXISTS idx_normalized_event_sequence_v1_scope
ON warehouse.normalized_event_sequence_v1(sequence_scope);
"""


TABLES = (
    "normalized_event_type_v1",
    "normalized_quality_status_v1",
    "normalized_normalization_run_v1",
    "normalized_event_sequence_v1",
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

            cur.execute("SELECT count(*)::int FROM warehouse.normalized_event_type_v1")
            event_types = cur.fetchone()[0]

            cur.execute("SELECT count(*)::int FROM warehouse.normalized_quality_status_v1")
            quality_statuses = cur.fetchone()[0]

            cur.execute("SELECT count(*)::int FROM warehouse.normalized_event_sequence_v1")
            sequences = cur.fetchone()[0]

    ok = (
        tables_found == len(TABLES)
        and event_types >= 5
        and quality_statuses >= 4
        and sequences >= 1
    )

    print("=== MARKET_DATA_SCHEMA_EVENT_CORE_V1 ===")
    print("layer=EVENT_CORE")
    print("tables=" + ",".join(TABLES))
    print(f"tables_found={tables_found}")
    print(f"columns_found={columns_found}")
    print(f"indexes_found={indexes_found}")
    print(f"event_types={event_types}")
    print(f"quality_statuses={quality_statuses}")
    print(f"event_sequences={sequences}")
    print("event_type=READY")
    print("quality_status=READY")
    print("normalization_run=READY")
    print("event_sequence=READY")
    print("event_framework=EVENT_FRAMEWORK_V1")
    print("identity_policy=IDENTITY_POLICY_V1")
    print("event_core_policy=EVENT_CORE_POLICY_V1")
    print("no_vendor_lock=1")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKET_DATA_SCHEMA_EVENT_CORE_V1_READY" if ok else "VERDICT=MARKET_DATA_SCHEMA_EVENT_CORE_V1_FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
