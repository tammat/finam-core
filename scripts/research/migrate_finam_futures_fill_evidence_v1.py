#!/usr/bin/env python3
from __future__ import annotations

import argparse

import psycopg2

from finam_core.analytics.statistics_repository import build_psycopg_url


DDL = """
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.futures_fill_evidence_v1 (
    fill_evidence_id       bigserial PRIMARY KEY,
    execution_ts           timestamptz NOT NULL,
    trade_date             date NOT NULL,
    symbol                 text NOT NULL,
    side                   text NOT NULL,
    quantity_contracts     numeric NOT NULL,
    price                  numeric NOT NULL,
    trade_id               text NOT NULL,
    order_id               text NOT NULL DEFAULT '',
    broker_account         text NOT NULL,
    source_document        text NOT NULL,
    source_reference       text NOT NULL,
    source_version         text NOT NULL,
    evidence_status        text NOT NULL,
    imported_at            timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT uq_futures_fill_evidence_v1
        UNIQUE (
            broker_account,
            trade_id,
            source_version
        ),

    CONSTRAINT ck_futures_fill_evidence_side
        CHECK (side IN ('BUY', 'SELL')),

    CONSTRAINT ck_futures_fill_evidence_quantity
        CHECK (quantity_contracts > 0),

    CONSTRAINT ck_futures_fill_evidence_price
        CHECK (price > 0),

    CONSTRAINT ck_futures_fill_evidence_status
        CHECK (
            evidence_status IN (
                'VERIFIED',
                'REVIEW_REQUIRED'
            )
        ),

    CONSTRAINT ck_futures_fill_evidence_symbol
        CHECK (position('@' IN symbol) > 1)
);

CREATE INDEX IF NOT EXISTS
    ix_futures_fill_evidence_v1_date_symbol
ON analytics.futures_fill_evidence_v1 (
    trade_date,
    symbol
);

CREATE INDEX IF NOT EXISTS
    ix_futures_fill_evidence_v1_execution_ts
ON analytics.futures_fill_evidence_v1 (
    execution_ts
);

CREATE INDEX IF NOT EXISTS
    ix_futures_fill_evidence_v1_source
ON analytics.futures_fill_evidence_v1 (
    source_version,
    evidence_status
);
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Finam Futures Fill Evidence Schema V1"
    )
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not args.apply:
        print("mode=plan_only")
        print("database=POSTGRESQL_ONLY")
        print("ddl_executed=0")
        print("schema_changed=0")
        print(
            "VERDICT="
            "FINAM_FUTURES_FILL_EVIDENCE_SCHEMA_PLAN_V1_READY"
        )
        return 0

    with psycopg2.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cursor:
            cursor.execute(DDL)

    print("mode=migration")
    print("database=POSTGRESQL_ONLY")
    print("ddl_executed=1")
    print("schema_changed=1")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "FINAM_FUTURES_FILL_EVIDENCE_SCHEMA_MIGRATION_V1_READY"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
