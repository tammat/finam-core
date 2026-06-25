#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import os
import sys

import psycopg2
import psycopg2.extras


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def ensure_table(cur) -> None:
    cur.execute("""
        CREATE SCHEMA IF NOT EXISTS research;

        CREATE TABLE IF NOT EXISTS research.shadow_runtime_runs_v1 (
            shadow_run_id BIGSERIAL PRIMARY KEY,
            queue_id BIGINT NOT NULL,
            candidate_id TEXT NOT NULL UNIQUE,
            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            run_status TEXT NOT NULL,
            run_reason TEXT NOT NULL,
            started_at TIMESTAMPTZ,
            finished_at TIMESTAMPTZ,
            runtime_changed BOOLEAN NOT NULL DEFAULT false,
            execution_changed BOOLEAN NOT NULL DEFAULT false,
            orders_changed BOOLEAN NOT NULL DEFAULT false,
            fills_changed BOOLEAN NOT NULL DEFAULT false,
            micro_live_allowed BOOLEAN NOT NULL DEFAULT false,
            payload JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_shadow_runtime_runs_status_v1
        ON research.shadow_runtime_runs_v1(run_status);
    """)


def build_runs(cur) -> int:
    ensure_table(cur)

    cur.execute("""
        INSERT INTO research.shadow_runtime_runs_v1 (
            queue_id,
            candidate_id,
            symbol,
            strategy,
            timeframe,
            run_status,
            run_reason,
            runtime_changed,
            execution_changed,
            orders_changed,
            fills_changed,
            micro_live_allowed,
            payload,
            updated_at
        )
        SELECT
            queue_id,
            candidate_id,
            symbol,
            strategy,
            timeframe,
            'PLANNED',
            'READY_FROM_SHADOW_RUNTIME_QUEUE',
            false,
            false,
            false,
            false,
            false,
            jsonb_build_object(
                'source', 'SHADOW_RUNTIME_ENGINE_V1',
                'queue_status', queue_status,
                'queue_reason', queue_reason,
                'runtime_changed', false,
                'execution_changed', false,
                'orders_changed', false,
                'fills_changed', false,
                'micro_live_allowed', false
            ),
            now()
        FROM research.shadow_runtime_queue_v1
        WHERE queue_status='READY'
        ON CONFLICT (candidate_id)
        DO UPDATE SET
            queue_id = EXCLUDED.queue_id,
            symbol = EXCLUDED.symbol,
            strategy = EXCLUDED.strategy,
            timeframe = EXCLUDED.timeframe,
            run_status = 'PLANNED',
            run_reason = 'READY_FROM_SHADOW_RUNTIME_QUEUE',
            runtime_changed = false,
            execution_changed = false,
            orders_changed = false,
            fills_changed = false,
            micro_live_allowed = false,
            payload = EXCLUDED.payload,
            updated_at = now()
    """)

    return int(cur.rowcount)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if args.save:
                changed_rows = build_runs(cur)
                conn.commit()
            else:
                ensure_table(cur)
                conn.rollback()
                changed_rows = 0

            cur.execute("""
                SELECT
                    count(*)::bigint AS rows_total,
                    sum(CASE WHEN run_status='PLANNED' THEN 1 ELSE 0 END)::bigint AS planned_rows
                FROM research.shadow_runtime_runs_v1
            """)
            summary = dict(cur.fetchone())

            cur.execute("""
                SELECT
                    candidate_id,
                    symbol,
                    strategy,
                    timeframe,
                    run_status,
                    run_reason
                FROM research.shadow_runtime_runs_v1
                ORDER BY updated_at DESC
                LIMIT 1
            """)
            last = cur.fetchone()

    print("=== SHADOW_RUNTIME_ENGINE_V1 ===")
    print(f"mode={'save' if args.save else 'dry_run'}")
    print(f"changed_rows={changed_rows}")
    print(f"rows_total={summary['rows_total']}")
    print(f"planned_rows={summary['planned_rows']}")

    if last:
        print(
            "run="
            f"{last['candidate_id']}|"
            f"{last['symbol']}|"
            f"{last['strategy']}|"
            f"{last['timeframe']}|"
            f"{last['run_status']}|"
            f"{last['run_reason']}"
        )

    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=SHADOW_RUNTIME_ENGINE_V1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
