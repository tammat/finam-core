#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import os
import sys

import psycopg2
import psycopg2.extras

from finam_core.execution.workflow.context import WorkflowContext
from finam_core.execution.workflow.stage_executor import StageExecutor


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def load_current_context(cur) -> WorkflowContext | None:
    cur.execute("""
        SELECT
            workflow_run_id,
            candidate_id,
            symbol,
            strategy,
            timeframe,
            workflow_type,
            workflow_version,
            current_stage,
            next_stage,
            payload
        FROM research.workflow_runtime_runs_v1
        WHERE workflow_type='PAPER_RUNTIME'
          AND workflow_version='v1'
          AND workflow_status='RUNNING'
        ORDER BY updated_at DESC
        LIMIT 1
    """)
    row = cur.fetchone()
    if not row:
        return None

    return WorkflowContext(
        workflow_run_id=int(row["workflow_run_id"]),
        candidate_id=row["candidate_id"],
        symbol=row["symbol"],
        strategy=row["strategy"],
        timeframe=row["timeframe"],
        workflow_type=row["workflow_type"],
        workflow_version=row["workflow_version"],
        current_stage=row["current_stage"],
        next_stage=row["next_stage"],
        payload=dict(row["payload"] or {}),
    )


def save_result_event(cur, context: WorkflowContext, result) -> None:
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
        VALUES (
            %s,
            %s,
            %s,
            %s,
            'STAGE_EXECUTED',
            %s,
            %s,
            now(),
            %s::jsonb
        )
    """, (
        context.workflow_run_id,
        context.candidate_id,
        context.current_stage,
        result.next_stage or context.current_stage,
        result.reason,
        result.status,
        psycopg2.extras.Json(result.payload),
    ))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            context = load_current_context(cur)
            if context is None:
                print("=== WORKFLOW_STAGE_EXECUTOR_ENGINE_V1 ===")
                print("mode=empty")
                print("stage_context_found=0")
                print("runtime_changed=0")
                print("execution_changed=0")
                print("orders_changed=0")
                print("fills_changed=0")
                print("micro_live_allowed=0")
                print("VERDICT=WORKFLOW_STAGE_EXECUTOR_ENGINE_V1_NO_CONTEXT")
                return 0

            result = StageExecutor().execute(context)

            if args.save:
                save_result_event(cur, context, result)
                conn.commit()
                event_saved = 1
            else:
                conn.rollback()
                event_saved = 0

    print("=== WORKFLOW_STAGE_EXECUTOR_ENGINE_V1 ===")
    print(f"mode={'save' if args.save else 'dry_run'}")
    print("stage_context_found=1")
    print(f"candidate_id={context.candidate_id}")
    print(f"current_stage={context.current_stage}")
    print(f"result_status={result.status}")
    print(f"result_next_stage={result.next_stage}")
    print(f"result_reason={result.reason}")
    print(f"event_saved={event_saved}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=WORKFLOW_STAGE_EXECUTOR_ENGINE_V1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
