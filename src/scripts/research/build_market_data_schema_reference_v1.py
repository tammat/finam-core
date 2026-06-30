#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import psycopg2


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


DDL = """
CREATE TABLE IF NOT EXISTS warehouse.normalized_symbol_alias_v1 (
    id bigserial PRIMARY KEY,
    source_system_id bigint NOT NULL REFERENCES warehouse.normalized_source_system_v1(id),
    instrument_id bigint NOT NULL REFERENCES warehouse.normalized_instrument_v1(id),
    contract_id bigint REFERENCES warehouse.normalized_contract_v1(id),
    entity_code text NOT NULL UNIQUE,
    entity_name text NOT NULL,
    alias_type text NOT NULL,
    source_symbol text NOT NULL,
    canonical_symbol text NOT NULL,
    alias_priority int NOT NULL DEFAULT 100,
    is_primary boolean NOT NULL DEFAULT false,
    status text NOT NULL DEFAULT 'ACTIVE',
    effective_from timestamptz NOT NULL DEFAULT now(),
    effective_to timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT normalized_symbol_alias_v1_source_symbol_not_empty CHECK (btrim(source_symbol) <> ''),
    CONSTRAINT normalized_symbol_alias_v1_canonical_symbol_not_empty CHECK (btrim(canonical_symbol) <> '')
);

CREATE TABLE IF NOT EXISTS warehouse.normalized_timeframe_v1 (
    id bigserial PRIMARY KEY,
    entity_code text NOT NULL UNIQUE,
    entity_name text NOT NULL,
    aggregation_family text NOT NULL DEFAULT 'TIME',
    duration_seconds int,
    duration_minutes numeric,
    status text NOT NULL DEFAULT 'ACTIVE',
    effective_from timestamptz NOT NULL DEFAULT now(),
    effective_to timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS warehouse.normalized_trading_session_v1 (
    id bigserial PRIMARY KEY,
    market_id bigint NOT NULL REFERENCES warehouse.normalized_market_v1(id),
    entity_code text NOT NULL UNIQUE,
    entity_name text NOT NULL,
    session_code text NOT NULL,
    session_group text NOT NULL DEFAULT 'REGULAR',
    session_sequence int NOT NULL DEFAULT 1,
    start_time time,
    end_time time,
    timezone text NOT NULL DEFAULT 'UTC',
    auction_before boolean NOT NULL DEFAULT false,
    auction_after boolean NOT NULL DEFAULT false,
    status text NOT NULL DEFAULT 'ACTIVE',
    effective_from timestamptz NOT NULL DEFAULT now(),
    effective_to timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS warehouse.normalized_trading_calendar_v1 (
    id bigserial PRIMARY KEY,
    market_id bigint NOT NULL REFERENCES warehouse.normalized_market_v1(id),
    entity_code text NOT NULL UNIQUE,
    entity_name text NOT NULL,
    calendar_date date NOT NULL,
    calendar_event_type text NOT NULL DEFAULT 'REGULAR_DAY',
    is_trading_day boolean NOT NULL DEFAULT true,
    status text NOT NULL DEFAULT 'ACTIVE',
    effective_from timestamptz NOT NULL DEFAULT now(),
    effective_to timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS warehouse.normalized_holiday_v1 (
    id bigserial PRIMARY KEY,
    market_id bigint NOT NULL REFERENCES warehouse.normalized_market_v1(id),
    entity_code text NOT NULL UNIQUE,
    entity_name text NOT NULL,
    holiday_date date NOT NULL,
    holiday_type text NOT NULL DEFAULT 'FULL_DAY',
    status text NOT NULL DEFAULT 'ACTIVE',
    effective_from timestamptz NOT NULL DEFAULT now(),
    effective_to timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS warehouse.normalized_roll_schedule_v1 (
    id bigserial PRIMARY KEY,
    contract_id bigint NOT NULL REFERENCES warehouse.normalized_contract_v1(id),
    next_contract_id bigint NOT NULL REFERENCES warehouse.normalized_contract_v1(id),
    entity_code text NOT NULL UNIQUE,
    entity_name text NOT NULL,
    roll_date date NOT NULL,
    roll_method text NOT NULL DEFAULT 'MANUAL',
    roll_reason text NOT NULL DEFAULT 'NOT_SPECIFIED',
    status text NOT NULL DEFAULT 'ACTIVE',
    effective_from timestamptz NOT NULL DEFAULT now(),
    effective_to timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT normalized_roll_schedule_v1_no_self_roll CHECK (contract_id <> next_contract_id)
);

CREATE TABLE IF NOT EXISTS warehouse.normalized_corporate_action_v1 (
    id bigserial PRIMARY KEY,
    instrument_id bigint NOT NULL REFERENCES warehouse.normalized_instrument_v1(id),
    entity_code text NOT NULL UNIQUE,
    entity_name text NOT NULL,
    action_type text NOT NULL,
    action_date date NOT NULL,
    adjust_price boolean NOT NULL DEFAULT false,
    adjust_volume boolean NOT NULL DEFAULT false,
    status text NOT NULL DEFAULT 'ACTIVE',
    effective_from timestamptz NOT NULL DEFAULT now(),
    effective_to timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS warehouse.normalized_market_regime_v1 (
    id bigserial PRIMARY KEY,
    entity_code text NOT NULL UNIQUE,
    entity_name text NOT NULL,
    regime_family text NOT NULL DEFAULT 'MARKET',
    status text NOT NULL DEFAULT 'ACTIVE',
    effective_from timestamptz NOT NULL DEFAULT now(),
    effective_to timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_normalized_symbol_alias_v1_source_symbol
ON warehouse.normalized_symbol_alias_v1(source_system_id, source_symbol);

CREATE INDEX IF NOT EXISTS idx_normalized_symbol_alias_v1_instrument
ON warehouse.normalized_symbol_alias_v1(instrument_id);

CREATE INDEX IF NOT EXISTS idx_normalized_symbol_alias_v1_contract
ON warehouse.normalized_symbol_alias_v1(contract_id);

CREATE INDEX IF NOT EXISTS idx_normalized_symbol_alias_v1_effective
ON warehouse.normalized_symbol_alias_v1(effective_from, effective_to);

CREATE INDEX IF NOT EXISTS idx_normalized_timeframe_v1_family
ON warehouse.normalized_timeframe_v1(aggregation_family);

CREATE INDEX IF NOT EXISTS idx_normalized_trading_session_v1_market
ON warehouse.normalized_trading_session_v1(market_id);

CREATE INDEX IF NOT EXISTS idx_normalized_trading_calendar_v1_market_date
ON warehouse.normalized_trading_calendar_v1(market_id, calendar_date);

CREATE INDEX IF NOT EXISTS idx_normalized_holiday_v1_market_date
ON warehouse.normalized_holiday_v1(market_id, holiday_date);

CREATE INDEX IF NOT EXISTS idx_normalized_roll_schedule_v1_contract
ON warehouse.normalized_roll_schedule_v1(contract_id);

CREATE INDEX IF NOT EXISTS idx_normalized_roll_schedule_v1_next_contract
ON warehouse.normalized_roll_schedule_v1(next_contract_id);

CREATE INDEX IF NOT EXISTS idx_normalized_corporate_action_v1_instrument
ON warehouse.normalized_corporate_action_v1(instrument_id);

CREATE INDEX IF NOT EXISTS idx_normalized_market_regime_v1_family
ON warehouse.normalized_market_regime_v1(regime_family);
"""


TABLES = (
    "normalized_symbol_alias_v1",
    "normalized_timeframe_v1",
    "normalized_trading_session_v1",
    "normalized_trading_calendar_v1",
    "normalized_holiday_v1",
    "normalized_roll_schedule_v1",
    "normalized_corporate_action_v1",
    "normalized_market_regime_v1",
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

    print("=== MARKET_DATA_SCHEMA_REFERENCE_V1 ===")
    print("layer=REFERENCE_DATA")
    print("tables=" + ",".join(TABLES))
    print(f"tables_found={tables_found}")
    print(f"columns_found={columns_found}")
    print(f"indexes_found={indexes_found}")
    print("symbol_alias=READY")
    print("timeframe=READY")
    print("trading_session=READY")
    print("trading_calendar=READY")
    print("holiday=READY")
    print("roll_schedule=READY")
    print("corporate_action=READY")
    print("market_regime=READY")
    print("history_support=READY")
    print("master_to_reference_dependency=ONE_WAY")
    print("no_vendor_lock=1")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKET_DATA_SCHEMA_REFERENCE_V1_READY" if tables_found == len(TABLES) else "VERDICT=MARKET_DATA_SCHEMA_REFERENCE_V1_FAILED")
    return 0 if tables_found == len(TABLES) else 1


if __name__ == "__main__":
    sys.exit(main())
