#!/usr/bin/env python3
from __future__ import annotations

import argparse

import psycopg2

from finam_core.analytics.statistics_repository import build_psycopg_url


DDL = r"""
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.cost_replay_run_v1 (
    replay_run_id            bigserial PRIMARY KEY,
    replay_uuid              uuid NOT NULL UNIQUE,
    source_run_uuid           uuid NOT NULL,
    research_batch_id         text,
    strategy_code             text NOT NULL,
    strategy_version          text NOT NULL,
    symbol                    text NOT NULL,
    timeframe                 text NOT NULL,
    parameter_hash            text NOT NULL,
    source_cost_model_version text NOT NULL,
    replay_cost_model_version text NOT NULL,
    replay_parameters         jsonb NOT NULL,
    status_code               text NOT NULL,
    failure_reason            text NOT NULL DEFAULT '',
    source_trade_count        integer NOT NULL DEFAULT 0,
    replay_trade_count        integer NOT NULL DEFAULT 0,
    created_at                timestamptz NOT NULL DEFAULT now(),
    started_at                timestamptz,
    finished_at               timestamptz,

    CONSTRAINT ck_cost_replay_run_status
        CHECK (
            status_code IN (
                'QUEUED',
                'RUNNING',
                'DONE',
                'FAILED',
                'BLOCKED'
            )
        ),

    CONSTRAINT uq_cost_replay_run_identity
        UNIQUE (
            source_run_uuid,
            replay_cost_model_version
        )
);

CREATE INDEX IF NOT EXISTS
    ix_cost_replay_run_v1_source_run_uuid
ON analytics.cost_replay_run_v1 (
    source_run_uuid
);

CREATE INDEX IF NOT EXISTS
    ix_cost_replay_run_v1_batch
ON analytics.cost_replay_run_v1 (
    research_batch_id
);

CREATE INDEX IF NOT EXISTS
    ix_cost_replay_run_v1_status
ON analytics.cost_replay_run_v1 (
    status_code
);

CREATE TABLE IF NOT EXISTS analytics.cost_replay_trade_v1 (
    replay_trade_id          bigserial PRIMARY KEY,
    replay_uuid              uuid NOT NULL,
    source_run_uuid          uuid NOT NULL,
    source_trade_no          integer NOT NULL,
    strategy_code            text NOT NULL,
    symbol                   text NOT NULL,
    timeframe                text NOT NULL,
    side                     text NOT NULL,
    entry_ts                 timestamptz NOT NULL,
    exit_ts                  timestamptz NOT NULL,
    entry_price              numeric NOT NULL,
    exit_price               numeric NOT NULL,
    quantity                 numeric NOT NULL,
    source_gross_pnl         numeric NOT NULL,
    source_commission        numeric NOT NULL,
    source_slippage          numeric NOT NULL,
    source_net_pnl           numeric NOT NULL,
    replay_broker_fee        numeric NOT NULL,
    replay_exchange_fee      numeric NOT NULL,
    replay_clearing_fee      numeric NOT NULL,
    replay_other_fee         numeric NOT NULL,
    replay_commission        numeric NOT NULL,
    replay_slippage          numeric NOT NULL,
    replay_net_pnl           numeric NOT NULL,
    cost_model_version       text NOT NULL,
    cost_evidence_status     text NOT NULL,
    cost_evidence_reference  text NOT NULL DEFAULT '',
    created_at               timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT fk_cost_replay_trade_run
        FOREIGN KEY (replay_uuid)
        REFERENCES analytics.cost_replay_run_v1 (
            replay_uuid
        )
        ON DELETE CASCADE,

    CONSTRAINT uq_cost_replay_trade_identity
        UNIQUE (
            replay_uuid,
            source_trade_no
        ),

    CONSTRAINT ck_cost_replay_trade_side
        CHECK (
            side IN ('LONG', 'SHORT', 'BUY', 'SELL')
        ),

    CONSTRAINT ck_cost_replay_trade_evidence
        CHECK (
            cost_evidence_status IN (
                'VERIFIED',
                'PROXY',
                'STORED',
                'MISSING'
            )
        )
);

CREATE INDEX IF NOT EXISTS
    ix_cost_replay_trade_v1_source_run_uuid
ON analytics.cost_replay_trade_v1 (
    source_run_uuid
);

CREATE INDEX IF NOT EXISTS
    ix_cost_replay_trade_v1_symbol
ON analytics.cost_replay_trade_v1 (
    symbol
);

CREATE TABLE IF NOT EXISTS analytics.cost_replay_result_v1 (
    replay_result_id          bigserial PRIMARY KEY,
    replay_uuid               uuid NOT NULL UNIQUE,
    source_run_uuid           uuid NOT NULL,
    strategy_code             text NOT NULL,
    symbol                    text NOT NULL,
    timeframe                 text NOT NULL,
    trades                    integer NOT NULL,
    wins                      integer NOT NULL,
    losses                    integer NOT NULL,
    win_rate                  numeric NOT NULL,
    gross_pnl                 numeric NOT NULL,
    source_commission         numeric NOT NULL,
    replay_commission         numeric NOT NULL,
    replay_slippage           numeric NOT NULL,
    replay_net_pnl            numeric NOT NULL,
    replay_expectancy         numeric NOT NULL,
    replay_profit_factor      numeric NOT NULL,
    cost_delta                numeric NOT NULL,
    net_pnl_delta             numeric NOT NULL,
    verdict_code              text NOT NULL,
    cost_model_version        text NOT NULL,
    cost_evidence_status      text NOT NULL,
    created_at                timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT fk_cost_replay_result_run
        FOREIGN KEY (replay_uuid)
        REFERENCES analytics.cost_replay_run_v1 (
            replay_uuid
        )
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS
    ix_cost_replay_result_v1_source_run_uuid
ON analytics.cost_replay_result_v1 (
    source_run_uuid
);

CREATE INDEX IF NOT EXISTS
    ix_cost_replay_result_v1_verdict
ON analytics.cost_replay_result_v1 (
    verdict_code
);
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
    )
    args = parser.parse_args()

    if not args.apply:
        print("mode=plan_only")
        print("database=POSTGRESQL_ONLY")
        print("ddl_executed=0")
        print("schema_changed=0")
        print("VERDICT=POSTGRESQL_COST_REPLAY_SCHEMA_PLAN_V1_READY")
        return 0

    with psycopg2.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)

    print("mode=migration")
    print("database=POSTGRESQL_ONLY")
    print("ddl_executed=1")
    print("schema_changed=1")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=POSTGRESQL_COST_REPLAY_SCHEMA_MIGRATION_V1_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
