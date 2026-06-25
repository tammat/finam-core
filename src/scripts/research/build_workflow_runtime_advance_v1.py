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


def advance(cur) -> int:
    cur.execute("""
        WITH current_runs AS (
            SELECT
                r.workflow_run_id,
                r.candidate_id,
                r.current_stage,
                r.next_stage,
                g.next_stage AS registry_next_stage
            FROM research.workflow_runtime_runs_v1 r
            JOIN research.workflow_stage_registry_v1 g
              ON g.workflow_type = r.workflow_type
             AND g.workflow_version = r.workflow_version
             AND g.stage_name = r.next_stage
             AND g.is_active = true
            WHERE r.workflow_type='PAPER_RUNTIME'
              AND r.workflow_version='v1'
              AND r.workflow_status='PLANNED'
              AND r.current_stage='QUEUE'
              AND r.next_stage='RISK'
        ),
        updated AS (
            UPDATE research.workflow_runtime_runs_v1 r
            SET
                workflow_status='RUNNING',
                current_stage=c.next_stage,
                next_stage=c.registry_next_stage,
                started_at=coalesce(r.started_at, now()),
                runtime_changed=false,
                execution_changed=false,
                orders_changed=false,
                fills_changed=false,
                micro_live_allowed=false,
                updated_at=now()
            FROM current_runs c
            WHERE r.workflow_run_id=c.workflow_run_id
            RETURNING
                r.workflow_run_id,
                r.candidate_id,
                c.current_stage AS stage_from,
                r.current_stage AS stage_to,
                r.next_stage
        )
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
            workflow_run_id,
            candidate_id,
            stage_from,
            stage_to,
            'STAGE_ADVANCED',
            'QUEUE_TO_RISK_BY_WORKFLOW_RUNTIME_ADVANCE_V1',
            'OK',
            now(),
            jsonb_build_object(
                'source', 'WORKFLOW_RUNTIME_ADVANCE_V1',
                'workflow_type', 'PAPER_RUNTIME',
                'workflow_version', 'v1',
                'stage_from', stage_from,
                'stage_to', stage_to,
                'next_stage', next_stage,
                'runtime_changed', false,
                'execution_changed', false,
                'orders_changed', false,
                'fills_changed', false,
                'micro_live_allowed', false
            )
        FROM updated
    """)
    return int(cur.rowcount)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if args.save:
                advanced_rows = advance(cur)
                conn.commit()
            else:
                advanced_rows = 0
                conn.rollback()

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

            cur.execute("""
                SELECT count(*)::bigint AS events_total
                FROM research.workflow_runtime_events_v1
            """)
            events = dict(cur.fetchone())

    print("=== WORKFLOW_RUNTIME_ADVANCE_V1 ===")
    print(f"mode={'save' if args.save else 'dry_run'}")
    print(f"advanced_rows={advanced_rows}")

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

    print(f"events_total={events['events_total']}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=WORKFLOW_RUNTIME_ADVANCE_V1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
