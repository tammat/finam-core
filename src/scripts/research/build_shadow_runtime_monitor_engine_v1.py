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

        CREATE TABLE IF NOT EXISTS research.shadow_runtime_monitor_v1 (
            monitor_id BIGSERIAL PRIMARY KEY,
            shadow_run_id BIGINT NOT NULL,
            candidate_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            run_status TEXT NOT NULL,
            transition_from TEXT,
            transition_to TEXT,
            transition_reason TEXT,
            heartbeat_ts TIMESTAMPTZ,
            latency_ms NUMERIC,
            runtime_seconds NUMERIC,
            queue_wait_seconds NUMERIC,
            event_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
            payload JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_shadow_runtime_monitor_run_event_v1
        ON research.shadow_runtime_monitor_v1(shadow_run_id, event_ts);

        CREATE INDEX IF NOT EXISTS idx_shadow_runtime_monitor_candidate_v1
        ON research.shadow_runtime_monitor_v1(candidate_id, event_ts);

        CREATE INDEX IF NOT EXISTS idx_shadow_runtime_monitor_status_v1
        ON research.shadow_runtime_monitor_v1(run_status, event_ts);
    """)


def insert_starting_events(cur) -> int:
    ensure_table(cur)

    cur.execute("""
        INSERT INTO research.shadow_runtime_monitor_v1 (
            shadow_run_id,
            candidate_id,
            symbol,
            strategy,
            timeframe,
            run_status,
            transition_from,
            transition_to,
            transition_reason,
            heartbeat_ts,
            latency_ms,
            runtime_seconds,
            queue_wait_seconds,
            event_ts,
            payload
        )
        SELECT
            r.shadow_run_id,
            r.candidate_id,
            r.symbol,
            r.strategy,
            r.timeframe,
            'STARTING',
            r.run_status,
            'STARTING',
            'PLANNED_TO_STARTING_BY_SHADOW_RUNTIME_MONITOR_ENGINE_V1',
            NULL,
            EXTRACT(EPOCH FROM (now() - r.updated_at)) * 1000,
            NULL,
            EXTRACT(EPOCH FROM (now() - r.created_at)),
            now(),
            jsonb_build_object(
                'source', 'SHADOW_RUNTIME_MONITOR_ENGINE_V1',
                'event_model', 'INSERT_ONLY',
                'runtime_changed', false,
                'execution_changed', false,
                'orders_changed', false,
                'fills_changed', false,
                'micro_live_allowed', false
            )
        FROM research.shadow_runtime_runs_v1 r
        WHERE r.run_status='PLANNED'
          AND NOT EXISTS (
              SELECT 1
              FROM research.shadow_runtime_monitor_v1 m
              WHERE m.shadow_run_id = r.shadow_run_id
                AND m.transition_from = 'PLANNED'
                AND m.transition_to = 'STARTING'
          )
    """)
    return int(cur.rowcount)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if args.save:
                inserted_rows = insert_starting_events(cur)
                conn.commit()
            else:
                ensure_table(cur)
                conn.rollback()
                inserted_rows = 0

            cur.execute("""
                SELECT
                    count(*)::bigint AS monitor_rows,
                    sum(CASE WHEN transition_from='PLANNED' AND transition_to='STARTING' THEN 1 ELSE 0 END)::bigint AS planned_to_starting_rows
                FROM research.shadow_runtime_monitor_v1
            """)
            summary = dict(cur.fetchone())

            cur.execute("""
                SELECT
                    candidate_id,
                    symbol,
                    strategy,
                    timeframe,
                    transition_from,
                    transition_to,
                    transition_reason
                FROM research.shadow_runtime_monitor_v1
                ORDER BY event_ts DESC, monitor_id DESC
                LIMIT 1
            """)
            last = cur.fetchone()

    print("=== SHADOW_RUNTIME_MONITOR_ENGINE_V1 ===")
    print(f"mode={'save' if args.save else 'dry_run'}")
    print(f"inserted_rows={inserted_rows}")
    print(f"monitor_rows={summary['monitor_rows']}")
    print(f"planned_to_starting_rows={summary['planned_to_starting_rows']}")

    if last:
        print(
            "monitor="
            f"{last['candidate_id']}|"
            f"{last['symbol']}|"
            f"{last['strategy']}|"
            f"{last['timeframe']}|"
            f"{last['transition_from']}->{last['transition_to']}|"
            f"{last['transition_reason']}"
        )

    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=SHADOW_RUNTIME_MONITOR_ENGINE_V1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
