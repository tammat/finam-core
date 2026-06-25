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


def apply_result(cur) -> int:
    cur.execute("""
        WITH last_ok AS (
            SELECT DISTINCT ON (e.workflow_run_id)
                e.workflow_run_id,
                e.candidate_id,
                e.stage_from,
                e.stage_to,
                e.event_reason
            FROM research.workflow_runtime_events_v1 e
            JOIN research.workflow_runtime_runs_v1 r
              ON r.workflow_run_id = e.workflow_run_id
            WHERE e.event_type='STAGE_EXECUTED'
              AND e.event_status='OK'
              AND r.workflow_status='RUNNING'
              AND r.current_stage=e.stage_from
              AND r.next_stage=e.stage_to
            ORDER BY e.workflow_run_id, e.event_ts DESC, e.event_id DESC
        ),
        registry_next AS (
            SELECT
                l.workflow_run_id,
                l.candidate_id,
                l.stage_from,
                l.stage_to,
                g.next_stage AS new_next_stage,
                l.event_reason
            FROM last_ok l
            LEFT JOIN research.workflow_stage_registry_v1 g
              ON g.workflow_type='PAPER_RUNTIME'
             AND g.workflow_version='v1'
             AND g.stage_name=l.stage_to
             AND g.is_active=true
        ),
        updated AS (
            UPDATE research.workflow_runtime_runs_v1 r
            SET
                current_stage = n.stage_to,
                next_stage = n.new_next_stage,
                workflow_status = CASE
                    WHEN n.stage_to='FINISHED' THEN 'COMPLETED'
                    ELSE 'RUNNING'
                END,
                finished_at = CASE
                    WHEN n.stage_to='FINISHED' THEN now()
                    ELSE r.finished_at
                END,
                runtime_changed=false,
                execution_changed=false,
                orders_changed=false,
                fills_changed=false,
                micro_live_allowed=false,
                updated_at=now()
            FROM registry_next n
            WHERE r.workflow_run_id=n.workflow_run_id
            RETURNING
                r.workflow_run_id,
                r.candidate_id,
                n.stage_from,
                n.stage_to,
                r.next_stage,
                r.workflow_status,
                n.event_reason
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
            'STAGE_RESULT_APPLIED',
            'APPLIED_OK_RESULT_FROM_' || event_reason,
            'OK',
            now(),
            jsonb_build_object(
                'source', 'WORKFLOW_STAGE_RESULT_APPLY_V1',
                'stage_from', stage_from,
                'stage_to', stage_to,
                'next_stage', next_stage,
                'workflow_status', workflow_status,
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
                applied_rows = apply_result(cur)
                conn.commit()
            else:
                applied_rows = 0
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
                SELECT count(*)::bigint AS applied_events
                FROM research.workflow_runtime_events_v1
                WHERE event_type='STAGE_RESULT_APPLIED'
                  AND stage_from='RISK'
                  AND stage_to='SIGNAL'
                  AND event_status='OK'
            """)
            events = dict(cur.fetchone())

    print("=== WORKFLOW_STAGE_RESULT_APPLY_V1 ===")
    print(f"mode={'save' if args.save else 'dry_run'}")
    print(f"applied_rows={applied_rows}")

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

    print(f"applied_events={events['applied_events']}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=WORKFLOW_STAGE_RESULT_APPLY_V1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
