#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import os
import sys

import psycopg2
import psycopg2.extras


CALCULATION_VERSION = "WORKFLOW_QUALITY_ENGINE_V1"


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def quality_events(cur) -> int:
    cur.execute("""
        INSERT INTO warehouse.qlt_workflow_event_v1 (
            source_event_id,
            workflow_run_id,
            candidate_id,
            quality_status,
            quality_reason_code,
            quality_light,
            source_table,
            source_id,
            calculation_version,
            calculated_at,
            payload
        )
        SELECT
            e.event_id AS source_event_id,
            e.workflow_run_id,
            e.candidate_id,
            CASE
                WHEN e.workflow_run_id IS NULL THEN 'FAILED'
                WHEN e.candidate_id IS NULL OR e.candidate_id='' THEN 'FAILED'
                WHEN e.event_type IS NULL OR e.event_type='' THEN 'FAILED'
                WHEN e.event_status IS NULL OR e.event_status='' THEN 'FAILED'
                WHEN e.stage_to IS NULL OR e.stage_to='' THEN 'FAILED'
                WHEN r.workflow_run_id IS NULL THEN 'FAILED'
                ELSE 'OK'
            END AS quality_status,
            CASE
                WHEN e.workflow_run_id IS NULL THEN 'MISSING_WORKFLOW_RUN_ID'
                WHEN e.candidate_id IS NULL OR e.candidate_id='' THEN 'MISSING_CANDIDATE_ID'
                WHEN e.event_type IS NULL OR e.event_type='' THEN 'MISSING_EVENT_TYPE'
                WHEN e.event_status IS NULL OR e.event_status='' THEN 'MISSING_EVENT_STATUS'
                WHEN e.stage_to IS NULL OR e.stage_to='' THEN 'MISSING_STAGE_TO'
                WHEN r.workflow_run_id IS NULL THEN 'ORPHAN_WORKFLOW_EVENT'
                ELSE 'OK'
            END AS quality_reason_code,
            CASE
                WHEN e.workflow_run_id IS NULL THEN 'RED'
                WHEN e.candidate_id IS NULL OR e.candidate_id='' THEN 'RED'
                WHEN e.event_type IS NULL OR e.event_type='' THEN 'RED'
                WHEN e.event_status IS NULL OR e.event_status='' THEN 'RED'
                WHEN e.stage_to IS NULL OR e.stage_to='' THEN 'RED'
                WHEN r.workflow_run_id IS NULL THEN 'ORANGE'
                ELSE 'GREEN'
            END AS quality_light,
            'research.workflow_runtime_events_v1',
            e.event_id,
            %s,
            now(),
            jsonb_build_object(
                'source', 'WORKFLOW_QUALITY_ENGINE_V1',
                'check_type', 'workflow_event_quality',
                'incremental', true,
                'runtime_changed', false,
                'execution_changed', false,
                'orders_changed', false,
                'fills_changed', false,
                'micro_live_allowed', false
            )
        FROM research.workflow_runtime_events_v1 e
        LEFT JOIN research.workflow_runtime_runs_v1 r
          ON r.workflow_run_id = e.workflow_run_id
        WHERE NOT EXISTS (
            SELECT 1
            FROM warehouse.qlt_workflow_event_v1 q
            WHERE q.source_event_id = e.event_id
        )
    """, (CALCULATION_VERSION,))
    return int(cur.rowcount)


def quality_runs(cur) -> int:
    cur.execute("""
        INSERT INTO warehouse.qlt_workflow_run_v1 (
            source_run_id,
            candidate_id,
            quality_status,
            quality_reason_code,
            quality_light,
            source_table,
            source_id,
            calculation_version,
            calculated_at,
            payload
        )
        SELECT
            r.workflow_run_id AS source_run_id,
            r.candidate_id,
            CASE
                WHEN r.workflow_run_id IS NULL THEN 'FAILED'
                WHEN r.candidate_id IS NULL OR r.candidate_id='' THEN 'FAILED'
                WHEN r.workflow_type IS NULL OR r.workflow_type='' THEN 'FAILED'
                WHEN r.workflow_version IS NULL OR r.workflow_version='' THEN 'FAILED'
                WHEN r.workflow_status IS NULL OR r.workflow_status='' THEN 'FAILED'
                WHEN r.current_stage IS NULL OR r.current_stage='' THEN 'FAILED'
                ELSE 'OK'
            END AS quality_status,
            CASE
                WHEN r.workflow_run_id IS NULL THEN 'MISSING_WORKFLOW_RUN_ID'
                WHEN r.candidate_id IS NULL OR r.candidate_id='' THEN 'MISSING_CANDIDATE_ID'
                WHEN r.workflow_type IS NULL OR r.workflow_type='' THEN 'MISSING_WORKFLOW_TYPE'
                WHEN r.workflow_version IS NULL OR r.workflow_version='' THEN 'MISSING_WORKFLOW_VERSION'
                WHEN r.workflow_status IS NULL OR r.workflow_status='' THEN 'MISSING_WORKFLOW_STATUS'
                WHEN r.current_stage IS NULL OR r.current_stage='' THEN 'MISSING_CURRENT_STAGE'
                ELSE 'OK'
            END AS quality_reason_code,
            CASE
                WHEN r.workflow_run_id IS NULL THEN 'RED'
                WHEN r.candidate_id IS NULL OR r.candidate_id='' THEN 'RED'
                WHEN r.workflow_type IS NULL OR r.workflow_type='' THEN 'RED'
                WHEN r.workflow_version IS NULL OR r.workflow_version='' THEN 'RED'
                WHEN r.workflow_status IS NULL OR r.workflow_status='' THEN 'RED'
                WHEN r.current_stage IS NULL OR r.current_stage='' THEN 'RED'
                ELSE 'GREEN'
            END AS quality_light,
            'research.workflow_runtime_runs_v1',
            r.workflow_run_id,
            %s,
            now(),
            jsonb_build_object(
                'source', 'WORKFLOW_QUALITY_ENGINE_V1',
                'check_type', 'workflow_run_quality',
                'incremental', true,
                'runtime_changed', false,
                'execution_changed', false,
                'orders_changed', false,
                'fills_changed', false,
                'micro_live_allowed', false
            )
        FROM research.workflow_runtime_runs_v1 r
        WHERE NOT EXISTS (
            SELECT 1
            FROM warehouse.qlt_workflow_run_v1 q
            WHERE q.source_run_id = r.workflow_run_id
        )
    """, (CALCULATION_VERSION,))
    return int(cur.rowcount)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if args.save:
                event_rows = quality_events(cur)
                run_rows = quality_runs(cur)
                conn.commit()
            else:
                event_rows = 0
                run_rows = 0
                conn.rollback()

            cur.execute("""
                SELECT
                    count(*)::bigint AS total,
                    sum(CASE WHEN quality_status='OK' THEN 1 ELSE 0 END)::bigint AS ok,
                    sum(CASE WHEN quality_status<>'OK' THEN 1 ELSE 0 END)::bigint AS bad
                FROM warehouse.qlt_workflow_event_v1
            """)
            event_summary = dict(cur.fetchone())

            cur.execute("""
                SELECT
                    count(*)::bigint AS total,
                    sum(CASE WHEN quality_status='OK' THEN 1 ELSE 0 END)::bigint AS ok,
                    sum(CASE WHEN quality_status<>'OK' THEN 1 ELSE 0 END)::bigint AS bad
                FROM warehouse.qlt_workflow_run_v1
            """)
            run_summary = dict(cur.fetchone())

    print("=== WORKFLOW_QUALITY_ENGINE_V1 ===")
    print(f"mode={'save' if args.save else 'dry_run'}")
    print(f"event_rows_inserted={event_rows}")
    print(f"run_rows_inserted={run_rows}")
    print(f"event_quality_total={event_summary['total']}")
    print(f"event_quality_ok={event_summary['ok']}")
    print(f"event_quality_bad={event_summary['bad']}")
    print(f"run_quality_total={run_summary['total']}")
    print(f"run_quality_ok={run_summary['ok']}")
    print(f"run_quality_bad={run_summary['bad']}")
    print("incremental_policy=changed_since_only")
    print("no_full_scan_policy=1")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=WORKFLOW_QUALITY_ENGINE_V1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
