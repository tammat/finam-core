#!/usr/bin/env python3

# ==========================================================
# MARKET_STATE_ENGINE_DATABASE_SCHEMA_APPLY_V1
#
# Применяет PostgreSQL DDL для таблиц Market State Engine.
#
# ВАЖНО:
# - только research schema;
# - PostgreSQL only;
# - SQLite запрещен;
# - Runtime не изменяется;
# - Execution не изменяется.
# ==========================================================

import os
import sys

import psycopg2


DDL = [
    "CREATE SCHEMA IF NOT EXISTS research;",
    """
    CREATE TABLE IF NOT EXISTS research.market_state_snapshots_v1 (
        snapshot_id BIGSERIAL PRIMARY KEY,
        snapshot_ts TIMESTAMPTZ NOT NULL,
        symbol TEXT NOT NULL,
        asset_class TEXT,
        timeframe TEXT NOT NULL,
        canonical_signature TEXT NOT NULL,
        compact_signature TEXT NOT NULL,
        quality TEXT NOT NULL,
        confidence NUMERIC,
        conflict_score NUMERIC,
        source TEXT NOT NULL DEFAULT 'market_state_engine_v1',
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE (snapshot_ts, symbol, timeframe, compact_signature)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS research.market_state_snapshot_values_v1 (
        snapshot_value_id BIGSERIAL PRIMARY KEY,
        snapshot_id BIGINT NOT NULL REFERENCES research.market_state_snapshots_v1(snapshot_id),
        state_group TEXT NOT NULL,
        state_code TEXT NOT NULL,
        confidence NUMERIC,
        classifier_version TEXT,
        explanation_ru TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE (snapshot_id, state_group)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS research.market_state_snapshot_metadata_v1 (
        snapshot_id BIGINT PRIMARY KEY REFERENCES research.market_state_snapshots_v1(snapshot_id),
        ontology_version TEXT NOT NULL,
        research_version TEXT NOT NULL,
        engine_version TEXT NOT NULL,
        classifier_versions JSONB NOT NULL DEFAULT '{}'::jsonb,
        explanation_tree_ru JSONB NOT NULL DEFAULT '[]'::jsonb,
        created_by TEXT NOT NULL DEFAULT 'market_state_engine_v1',
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS research.market_state_transitions_v1 (
        transition_id BIGSERIAL PRIMARY KEY,
        symbol TEXT NOT NULL,
        timeframe TEXT NOT NULL,
        snapshot_from BIGINT NOT NULL REFERENCES research.market_state_snapshots_v1(snapshot_id),
        snapshot_to BIGINT NOT NULL REFERENCES research.market_state_snapshots_v1(snapshot_id),
        transition_type TEXT NOT NULL,
        duration_seconds BIGINT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE (snapshot_from, snapshot_to)
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_market_state_snapshots_symbol_ts
    ON research.market_state_snapshots_v1(symbol, snapshot_ts);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_market_state_snapshots_compact_signature
    ON research.market_state_snapshots_v1(compact_signature);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_market_state_snapshot_values_snapshot
    ON research.market_state_snapshot_values_v1(snapshot_id);
    """,
]


def main() -> int:
    print("=== MARKET_STATE_ENGINE_DATABASE_SCHEMA_APPLY_V1 ===")
    print("mode=schema_apply")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("orders_sent=0")

    if "--apply" not in sys.argv:
        print("db_update=0")
        print("VERDICT=MARKET_STATE_ENGINE_DATABASE_SCHEMA_APPLY_REQUIRES_APPLY_FLAG")
        return 2

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("db_update=0")
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2

    if database_url.startswith("sqlite"):
        print("db_update=0")
        print("ERROR=SQLITE_FORBIDDEN_POSTGRES_REQUIRED")
        return 2

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            for statement in DDL:
                cur.execute(statement)
        conn.commit()

    print("db_update=1")
    print("tables_applied=4")
    print("indexes_applied=3")
    print("schema=research")
    print("VERDICT=MARKET_STATE_ENGINE_DATABASE_SCHEMA_APPLY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
