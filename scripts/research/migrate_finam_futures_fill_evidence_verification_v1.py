#!/usr/bin/env python3
from __future__ import annotations

import argparse

import psycopg2

from finam_core.analytics.statistics_repository import build_psycopg_url


DDL = """
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS
analytics.futures_fill_evidence_verification_v1 (
    verification_id             bigserial PRIMARY KEY,
    verification_batch_id       text NOT NULL,
    source_version              text NOT NULL,
    trade_date                  date NOT NULL,
    broker_account              text NOT NULL,
    fill_row_count              integer NOT NULL,
    contract_sides              numeric NOT NULL,
    fee_per_contract_side       numeric NOT NULL,
    calculated_commission       numeric NOT NULL,
    reported_commission         numeric NOT NULL,
    reconciliation_delta        numeric NOT NULL,
    reconciliation_status       text NOT NULL,
    reviewed_fill_count         integer NOT NULL,
    verified_fill_count         integer NOT NULL,
    verification_reason         text NOT NULL,
    created_at                  timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT uq_futures_fill_verification_v1
        UNIQUE (
            verification_batch_id,
            source_version,
            trade_date,
            broker_account
        ),

    CONSTRAINT ck_futures_fill_verification_status
        CHECK (
            reconciliation_status IN (
                'MATCH',
                'MISMATCH',
                'COMMISSION_MISSING',
                'FILLS_MISSING'
            )
        )
);

CREATE INDEX IF NOT EXISTS
    ix_futures_fill_verification_v1_source
ON analytics.futures_fill_evidence_verification_v1 (
    source_version,
    trade_date
);

CREATE OR REPLACE VIEW
analytics.v_futures_fill_evidence_verified_v1 AS
SELECT
    fill_evidence_id,
    execution_ts,
    trade_date,
    symbol,
    side,
    quantity_contracts,
    price,
    trade_id,
    order_id,
    broker_account,
    source_document,
    source_reference,
    source_version,
    evidence_status,
    imported_at
FROM analytics.futures_fill_evidence_v1
WHERE evidence_status = 'VERIFIED';
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not args.apply:
        print("mode=plan_only")
        print("ddl_executed=0")
        print(
            "VERDICT="
            "FINAM_FUTURES_FILL_EVIDENCE_VERIFICATION_SCHEMA_PLAN_V1_READY"
        )
        return 0

    with psycopg2.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)

    print("ddl_executed=1")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "FINAM_FUTURES_FILL_EVIDENCE_VERIFICATION_SCHEMA_V1_READY"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
