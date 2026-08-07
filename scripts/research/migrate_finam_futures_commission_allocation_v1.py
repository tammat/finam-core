#!/usr/bin/env python3
from __future__ import annotations

import argparse

import psycopg2

from finam_core.analytics.statistics_repository import build_psycopg_url


DDL = """
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.futures_commission_daily_v1 (
    daily_commission_id      bigserial PRIMARY KEY,
    trade_date               date NOT NULL,
    broker_account           text NOT NULL,
    commission_total         numeric NOT NULL,
    currency_code            text NOT NULL DEFAULT 'RUB',
    source_document          text NOT NULL,
    source_reference         text NOT NULL,
    source_version           text NOT NULL,
    evidence_status          text NOT NULL,
    created_at               timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT uq_futures_commission_daily_v1
        UNIQUE (
            trade_date,
            broker_account,
            source_version
        ),

    CONSTRAINT ck_futures_commission_daily_positive
        CHECK (commission_total > 0),

    CONSTRAINT ck_futures_commission_daily_evidence
        CHECK (
            evidence_status IN (
                'VERIFIED',
                'REVIEW_REQUIRED'
            )
        )
);

CREATE INDEX IF NOT EXISTS
    ix_futures_commission_daily_v1_trade_date
ON analytics.futures_commission_daily_v1 (
    trade_date
);

CREATE TABLE IF NOT EXISTS analytics.futures_commission_allocation_v1 (
    allocation_id             bigserial PRIMARY KEY,
    allocation_batch_id       text NOT NULL,
    trade_date                date NOT NULL,
    broker_account            text NOT NULL,
    allocation_model          text NOT NULL,
    symbol                    text NOT NULL,
    executed_contracts        numeric NOT NULL,
    turnover                  numeric NOT NULL,
    allocation_basis_value    numeric NOT NULL,
    allocation_weight         numeric NOT NULL,
    daily_commission_total     numeric NOT NULL,
    allocated_commission      numeric NOT NULL,
    commission_per_contract   numeric NOT NULL,
    source_fills_table        text NOT NULL,
    source_document           text NOT NULL,
    source_reference          text NOT NULL,
    source_version            text NOT NULL,
    evidence_status           text NOT NULL,
    created_at                timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT uq_futures_commission_allocation_v1
        UNIQUE (
            allocation_batch_id,
            trade_date,
            allocation_model,
            symbol
        ),

    CONSTRAINT ck_futures_allocation_model
        CHECK (
            allocation_model IN (
                'CONTRACT_COUNT',
                'TURNOVER'
            )
        ),

    CONSTRAINT ck_futures_allocation_contracts
        CHECK (executed_contracts > 0),

    CONSTRAINT ck_futures_allocation_weight
        CHECK (
            allocation_weight > 0
            AND allocation_weight <= 1
        ),

    CONSTRAINT ck_futures_allocation_values
        CHECK (
            turnover >= 0
            AND allocation_basis_value > 0
            AND daily_commission_total > 0
            AND allocated_commission > 0
            AND commission_per_contract > 0
        ),

    CONSTRAINT ck_futures_allocation_evidence
        CHECK (
            evidence_status IN (
                'VERIFIED',
                'REVIEW_REQUIRED'
            )
        )
);

CREATE INDEX IF NOT EXISTS
    ix_futures_commission_allocation_v1_lookup
ON analytics.futures_commission_allocation_v1 (
    trade_date,
    symbol,
    allocation_model
);

CREATE INDEX IF NOT EXISTS
    ix_futures_commission_allocation_v1_batch
ON analytics.futures_commission_allocation_v1 (
    allocation_batch_id
);
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not args.apply:
        print("mode=plan_only")
        print("database=POSTGRESQL_ONLY")
        print("ddl_executed=0")
        print("schema_changed=0")
        print(
            "VERDICT="
            "FINAM_FUTURES_COMMISSION_ALLOCATION_SCHEMA_PLAN_V1_READY"
        )
        return 0

    with psycopg2.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cursor:
            cursor.execute(DDL)

    print("mode=migration")
    print("database=POSTGRESQL_ONLY")
    print("ddl_executed=1")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "FINAM_FUTURES_COMMISSION_ALLOCATION_SCHEMA_MIGRATION_V1_READY"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
