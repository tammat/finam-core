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


def ensure_tables(cur) -> None:
    cur.execute("""
        CREATE SCHEMA IF NOT EXISTS research;

        CREATE TABLE IF NOT EXISTS research.workflow_stage_registry_v1 (
            stage_id BIGSERIAL PRIMARY KEY,
            workflow_type TEXT NOT NULL,
            workflow_version TEXT NOT NULL,
            stage_name TEXT NOT NULL,
            next_stage TEXT,
            stage_order INTEGER NOT NULL,
            is_terminal BOOLEAN NOT NULL DEFAULT false,
            is_active BOOLEAN NOT NULL DEFAULT true,
            payload JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (workflow_type, workflow_version, stage_name)
        );

        CREATE TABLE IF NOT EXISTS research.workflow_runtime_runs_v1 (
            workflow_run_id BIGSERIAL PRIMARY KEY,
            workflow_type TEXT NOT NULL,
            workflow_version TEXT NOT NULL,
            candidate_id TEXT NOT NULL UNIQUE,
            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            workflow_status TEXT NOT NULL,
            current_stage TEXT NOT NULL,
            next_stage TEXT,
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

        CREATE TABLE IF NOT EXISTS research.workflow_runtime_events_v1 (
            event_id BIGSERIAL PRIMARY KEY,
            workflow_run_id BIGINT NOT NULL,
            candidate_id TEXT NOT NULL,
            stage_from TEXT,
            stage_to TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_reason TEXT NOT NULL,
            event_status TEXT NOT NULL,
            event_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
            payload JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_workflow_registry_type_version_order_v1
        ON research.workflow_stage_registry_v1(workflow_type, workflow_version, stage_order);

        CREATE INDEX IF NOT EXISTS idx_workflow_runs_status_stage_v1
        ON research.workflow_runtime_runs_v1(workflow_status, current_stage);

        CREATE INDEX IF NOT EXISTS idx_workflow_events_run_ts_v1
        ON research.workflow_runtime_events_v1(workflow_run_id, event_ts);
    """)


def upsert_registry(cur) -> int:
    stages = [
        ("QUEUE", "RISK", 1, False),
        ("RISK", "SIGNAL", 2, False),
        ("SIGNAL", "ORDER", 3, False),
        ("ORDER", "PAPER_BROKER", 4, False),
        ("PAPER_BROKER", "ACCOUNTING", 5, False),
        ("ACCOUNTING", "MONITOR", 6, False),
        ("MONITOR", "FINISHED", 7, False),
        ("FINISHED", None, 8, True),
    ]

    changed = 0
    for stage_name, next_stage, stage_order, is_terminal in stages:
        cur.execute(
            """
            INSERT INTO research.workflow_stage_registry_v1 (
                workflow_type,
                workflow_version,
                stage_name,
                next_stage,
                stage_order,
                is_terminal,
                is_active,
                payload,
                updated_at
            )
            VALUES (
                'PAPER_RUNTIME',
                'v1',
                %s,
                %s,
                %s,
                %s,
                true,
                jsonb_build_object(
                    'source', 'WORKFLOW_RUNTIME_ENGINE_V1',
                    'paper_only', true,
                    'real_execution', false,
                    'micro_live_allowed', false
                ),
                now()
            )
            ON CONFLICT (workflow_type, workflow_version, stage_name)
            DO UPDATE SET
                next_stage = EXCLUDED.next_stage,
                stage_order = EXCLUDED.stage_order,
                is_terminal = EXCLUDED.is_terminal,
                is_active = true,
                payload = EXCLUDED.payload,
                updated_at = now()
            """,
            (stage_name, next_stage, stage_order, is_terminal),
        )
        changed += cur.rowcount

    return changed


def upsert_workflow_runs(cur) -> int:
    cur.execute("""
        INSERT INTO research.workflow_runtime_runs_v1 (
            workflow_type,
            workflow_version,
            candidate_id,
            symbol,
            strategy,
            timeframe,
            workflow_status,
            current_stage,
            next_stage,
            started_at,
            finished_at,
            runtime_changed,
            execution_changed,
            orders_changed,
            fills_changed,
            micro_live_allowed,
            payload,
            updated_at
        )
        SELECT
            'PAPER_RUNTIME',
            'v1',
            s.candidate_id,
            s.symbol,
            s.strategy,
            s.timeframe,
            'PLANNED',
            'QUEUE',
            'RISK',
            NULL,
            NULL,
            false,
            false,
            false,
            false,
            false,
            jsonb_build_object(
                'source', 'WORKFLOW_RUNTIME_ENGINE_V1',
                'source_table', 'research.shadow_runtime_scorecard_v1',
                'scheduler_mode', 'MULTI_CANDIDATE',
                'execution_mode', 'PAPER_ONLY',
                'broker_mode', 'NO_REAL_BROKER',
                'runtime_changed', false,
                'execution_changed', false,
                'orders_changed', false,
                'fills_changed', false,
                'micro_live_allowed', false
            ),
            now()
        FROM research.shadow_runtime_scorecard_v1 s
        WHERE s.total_events >= 1
          AND s.failed_events = 0
          AND s.timeout_events = 0
          AND s.cancelled_events = 0
        ON CONFLICT (candidate_id)
        DO UPDATE SET
            workflow_type = EXCLUDED.workflow_type,
            workflow_version = EXCLUDED.workflow_version,
            symbol = EXCLUDED.symbol,
            strategy = EXCLUDED.strategy,
            timeframe = EXCLUDED.timeframe,
            workflow_status = EXCLUDED.workflow_status,
            current_stage = EXCLUDED.current_stage,
            next_stage = EXCLUDED.next_stage,
            runtime_changed = false,
            execution_changed = false,
            orders_changed = false,
            fills_changed = false,
            micro_live_allowed = false,
            payload = EXCLUDED.payload,
            updated_at = now()
    """)
    return int(cur.rowcount)


def insert_created_events(cur) -> int:
    cur.execute("""
        INSERT INTO research.workflow_runtime_events_v1 (
            workflow_run_id,
            candidate_id,
            stage_from,
            stage_to,
            event_type,
            event_reason,
            event_status,
            event_ts,
            payload
        )
        SELECT
            r.workflow_run_id,
            r.candidate_id,
            NULL,
            r.current_stage,
            'WORKFLOW_CREATED',
            'CREATED_FROM_SHADOW_RUNTIME_SCORECARD',
            'OK',
            now(),
            jsonb_build_object(
                'source', 'WORKFLOW_RUNTIME_ENGINE_V1',
                'workflow_type', r.workflow_type,
                'workflow_version', r.workflow_version,
                'current_stage', r.current_stage,
                'next_stage', r.next_stage,
                'runtime_changed', false,
                'execution_changed', false,
                'orders_changed', false,
                'fills_changed', false,
                'micro_live_allowed', false
            )
        FROM research.workflow_runtime_runs_v1 r
        WHERE r.workflow_type='PAPER_RUNTIME'
          AND r.workflow_version='v1'
          AND NOT EXISTS (
              SELECT 1
              FROM research.workflow_runtime_events_v1 e
              WHERE e.workflow_run_id = r.workflow_run_id
                AND e.event_type = 'WORKFLOW_CREATED'
          )
    """)
    return int(cur.rowcount)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            ensure_tables(cur)

            if args.save:
                registry_changed = upsert_registry(cur)
                run_changed = upsert_workflow_runs(cur)
                event_inserted = insert_created_events(cur)
                conn.commit()
            else:
                registry_changed = 0
                run_changed = 0
                event_inserted = 0
                conn.rollback()

            cur.execute("""
                SELECT count(*)::bigint AS registry_rows
                FROM research.workflow_stage_registry_v1
                WHERE workflow_type='PAPER_RUNTIME'
                  AND workflow_version='v1'
                  AND is_active=true
            """)
            registry = dict(cur.fetchone())

            cur.execute("""
                SELECT
                    count(*)::bigint AS workflow_rows,
                    sum(CASE WHEN workflow_status='PLANNED' THEN 1 ELSE 0 END)::bigint AS planned_rows
                FROM research.workflow_runtime_runs_v1
                WHERE workflow_type='PAPER_RUNTIME'
                  AND workflow_version='v1'
            """)
            runs = dict(cur.fetchone())

            cur.execute("""
                SELECT count(*)::bigint AS event_rows
                FROM research.workflow_runtime_events_v1
                WHERE event_type='WORKFLOW_CREATED'
            """)
            events = dict(cur.fetchone())

            cur.execute("""
                SELECT
                    candidate_id,
                    symbol,
                    strategy,
                    timeframe,
                    workflow_status,
                    current_stage,
                    next_stage
                FROM research.workflow_runtime_runs_v1
                WHERE workflow_type='PAPER_RUNTIME'
                  AND workflow_version='v1'
                ORDER BY updated_at DESC
                LIMIT 1
            """)
            last = cur.fetchone()

    print("=== WORKFLOW_RUNTIME_ENGINE_V1 ===")
    print(f"mode={'save' if args.save else 'dry_run'}")
    print(f"registry_changed={registry_changed}")
    print(f"run_changed={run_changed}")
    print(f"event_inserted={event_inserted}")
    print(f"registry_rows={registry['registry_rows']}")
    print(f"workflow_rows={runs['workflow_rows']}")
    print(f"planned_rows={runs['planned_rows']}")
    print(f"workflow_created_events={events['event_rows']}")

    if last:
        print(
            "workflow="
            f"{last['candidate_id']}|"
            f"{last['symbol']}|"
            f"{last['strategy']}|"
            f"{last['timeframe']}|"
            f"status={last['workflow_status']}|"
            f"current={last['current_stage']}|"
            f"next={last['next_stage']}"
        )

    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=WORKFLOW_RUNTIME_ENGINE_V1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
