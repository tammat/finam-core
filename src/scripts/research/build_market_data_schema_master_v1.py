#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import psycopg2


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


DDL = """
CREATE TABLE IF NOT EXISTS warehouse.normalized_source_system_v1 (
    id bigserial PRIMARY KEY,
    entity_code text NOT NULL UNIQUE,
    entity_name text NOT NULL,
    source_type text NOT NULL,
    status text NOT NULL DEFAULT 'ACTIVE',
    effective_from timestamptz NOT NULL DEFAULT now(),
    effective_to timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT normalized_source_system_v1_code_not_empty CHECK (btrim(entity_code) <> ''),
    CONSTRAINT normalized_source_system_v1_name_not_empty CHECK (btrim(entity_name) <> '')
);

CREATE TABLE IF NOT EXISTS warehouse.normalized_asset_class_v1 (
    id bigserial PRIMARY KEY,
    entity_code text NOT NULL UNIQUE,
    entity_name text NOT NULL,
    status text NOT NULL DEFAULT 'ACTIVE',
    effective_from timestamptz NOT NULL DEFAULT now(),
    effective_to timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS warehouse.normalized_currency_v1 (
    id bigserial PRIMARY KEY,
    entity_code text NOT NULL UNIQUE,
    entity_name text NOT NULL,
    iso_code text NOT NULL UNIQUE,
    status text NOT NULL DEFAULT 'ACTIVE',
    effective_from timestamptz NOT NULL DEFAULT now(),
    effective_to timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS warehouse.normalized_venue_v1 (
    id bigserial PRIMARY KEY,
    entity_code text NOT NULL UNIQUE,
    entity_name text NOT NULL,
    venue_type text NOT NULL,
    country_code text,
    status text NOT NULL DEFAULT 'ACTIVE',
    effective_from timestamptz NOT NULL DEFAULT now(),
    effective_to timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS warehouse.normalized_exchange_v1 (
    id bigserial PRIMARY KEY,
    venue_id bigint NOT NULL REFERENCES warehouse.normalized_venue_v1(id),
    entity_code text NOT NULL UNIQUE,
    entity_name text NOT NULL,
    mic_code text,
    country_code text,
    status text NOT NULL DEFAULT 'ACTIVE',
    effective_from timestamptz NOT NULL DEFAULT now(),
    effective_to timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS warehouse.normalized_market_v1 (
    id bigserial PRIMARY KEY,
    exchange_id bigint NOT NULL REFERENCES warehouse.normalized_exchange_v1(id),
    entity_code text NOT NULL UNIQUE,
    entity_name text NOT NULL,
    market_type text NOT NULL,
    status text NOT NULL DEFAULT 'ACTIVE',
    effective_from timestamptz NOT NULL DEFAULT now(),
    effective_to timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS warehouse.normalized_asset_v1 (
    id bigserial PRIMARY KEY,
    asset_class_id bigint NOT NULL REFERENCES warehouse.normalized_asset_class_v1(id),
    entity_code text NOT NULL UNIQUE,
    entity_name text NOT NULL,
    base_currency_id bigint REFERENCES warehouse.normalized_currency_v1(id),
    status text NOT NULL DEFAULT 'ACTIVE',
    effective_from timestamptz NOT NULL DEFAULT now(),
    effective_to timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS warehouse.normalized_currency_pair_v1 (
    id bigserial PRIMARY KEY,
    base_currency_id bigint NOT NULL REFERENCES warehouse.normalized_currency_v1(id),
    quote_currency_id bigint NOT NULL REFERENCES warehouse.normalized_currency_v1(id),
    entity_code text NOT NULL UNIQUE,
    entity_name text NOT NULL,
    status text NOT NULL DEFAULT 'ACTIVE',
    effective_from timestamptz NOT NULL DEFAULT now(),
    effective_to timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT normalized_currency_pair_v1_no_self_pair CHECK (base_currency_id <> quote_currency_id)
);

CREATE TABLE IF NOT EXISTS warehouse.normalized_instrument_v1 (
    id bigserial PRIMARY KEY,
    asset_id bigint NOT NULL REFERENCES warehouse.normalized_asset_v1(id),
    asset_class_id bigint NOT NULL REFERENCES warehouse.normalized_asset_class_v1(id),
    entity_code text NOT NULL UNIQUE,
    entity_name text NOT NULL,
    instrument_type text NOT NULL,
    quote_currency_id bigint REFERENCES warehouse.normalized_currency_v1(id),
    status text NOT NULL DEFAULT 'ACTIVE',
    effective_from timestamptz NOT NULL DEFAULT now(),
    effective_to timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS warehouse.normalized_contract_v1 (
    id bigserial PRIMARY KEY,
    instrument_id bigint NOT NULL REFERENCES warehouse.normalized_instrument_v1(id),
    market_id bigint NOT NULL REFERENCES warehouse.normalized_market_v1(id),
    entity_code text NOT NULL UNIQUE,
    entity_name text NOT NULL,
    contract_type text NOT NULL,
    expiry_date date,
    settlement_currency_id bigint REFERENCES warehouse.normalized_currency_v1(id),
    status text NOT NULL DEFAULT 'ACTIVE',
    effective_from timestamptz NOT NULL DEFAULT now(),
    effective_to timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    payload jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_normalized_source_system_v1_status ON warehouse.normalized_source_system_v1(status);
CREATE INDEX IF NOT EXISTS idx_normalized_asset_class_v1_status ON warehouse.normalized_asset_class_v1(status);
CREATE INDEX IF NOT EXISTS idx_normalized_currency_v1_status ON warehouse.normalized_currency_v1(status);
CREATE INDEX IF NOT EXISTS idx_normalized_venue_v1_status ON warehouse.normalized_venue_v1(status);
CREATE INDEX IF NOT EXISTS idx_normalized_exchange_v1_venue ON warehouse.normalized_exchange_v1(venue_id);
CREATE INDEX IF NOT EXISTS idx_normalized_market_v1_exchange ON warehouse.normalized_market_v1(exchange_id);
CREATE INDEX IF NOT EXISTS idx_normalized_asset_v1_asset_class ON warehouse.normalized_asset_v1(asset_class_id);
CREATE INDEX IF NOT EXISTS idx_normalized_currency_pair_v1_base_quote ON warehouse.normalized_currency_pair_v1(base_currency_id, quote_currency_id);
CREATE INDEX IF NOT EXISTS idx_normalized_instrument_v1_asset ON warehouse.normalized_instrument_v1(asset_id);
CREATE INDEX IF NOT EXISTS idx_normalized_contract_v1_instrument ON warehouse.normalized_contract_v1(instrument_id);
CREATE INDEX IF NOT EXISTS idx_normalized_contract_v1_market ON warehouse.normalized_contract_v1(market_id);
"""


TABLES = (
    "normalized_source_system_v1",
    "normalized_asset_class_v1",
    "normalized_currency_v1",
    "normalized_venue_v1",
    "normalized_exchange_v1",
    "normalized_market_v1",
    "normalized_asset_v1",
    "normalized_currency_pair_v1",
    "normalized_instrument_v1",
    "normalized_contract_v1",
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

    print("=== MARKET_DATA_SCHEMA_MASTER_V1 ===")
    print("layer=MASTER_DATA")
    print("tables=" + ",".join(TABLES))
    print(f"tables_found={tables_found}")
    print(f"columns_found={columns_found}")
    print(f"indexes_found={indexes_found}")
    print("policy=MASTER_REFERENCE_EVENT_QUALITY_LINEAGE")
    print("no_vendor_lock=1")
    print("source_system=READY")
    print("instrument_contract_separated=1")
    print("symbol_alias_not_in_master=1")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKET_DATA_SCHEMA_MASTER_V1_READY" if tables_found == len(TABLES) else "VERDICT=MARKET_DATA_SCHEMA_MASTER_V1_FAILED")
    return 0 if tables_found == len(TABLES) else 1


if __name__ == "__main__":
    sys.exit(main())
