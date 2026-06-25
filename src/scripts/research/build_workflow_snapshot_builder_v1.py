#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import os
import sys

import psycopg2
import psycopg2.extras


SNAPSHOT_VERSION = "WORKFLOW_SNAPSHOT_BUILDER_V1"


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def ensure_schema(cur) -> None:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS warehouse.snap_workflow_daily_v1 (
            snapshot_id BIGSERIAL PRIMARY KEY,
            snapshot_date DATE NOT NULL,
            snapshot_type TEXT NOT NULL,
            section_code TEXT NOT NULL,
            metric_code TEXT NOT NULL,
            metric_value TEXT,
            health_score NUMERIC,
            health_light TEXT,
            health_icon TEXT,
            health_reason_code TEXT,
            candidate_id TEXT,
            workflow_run_id BIGINT,
            mart_version TEXT,
            snapshot_version TEXT,
            source_table TEXT,
            calculated_at TIMESTAMPTZ DEFAULT now(),
            payload JSONB DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    """)

    cur.execute("""
        ALTER TABLE warehouse.snap_workflow_daily_v1
        ADD COLUMN IF NOT EXISTS snapshot_date DATE,
        ADD COLUMN IF NOT EXISTS snapshot_type TEXT,
        ADD COLUMN IF NOT EXISTS section_code TEXT,
        ADD COLUMN IF NOT EXISTS metric_code TEXT,
        ADD COLUMN IF NOT EXISTS metric_value TEXT,
        ADD COLUMN IF NOT EXISTS health_score NUMERIC,
        ADD COLUMN IF NOT EXISTS health_light TEXT,
        ADD COLUMN IF NOT EXISTS health_icon TEXT,
        ADD COLUMN IF NOT EXISTS health_reason_code TEXT,
        ADD COLUMN IF NOT EXISTS candidate_id TEXT,
        ADD COLUMN IF NOT EXISTS workflow_run_id BIGINT,
        ADD COLUMN IF NOT EXISTS mart_version TEXT,
        ADD COLUMN IF NOT EXISTS snapshot_version TEXT,
        ADD COLUMN IF NOT EXISTS source_table TEXT,
        ADD COLUMN IF NOT EXISTS calculated_at TIMESTAMPTZ DEFAULT now(),
        ADD COLUMN IF NOT EXISTS payload JSONB DEFAULT '{}'::jsonb,
        ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now()
    """)

    cur.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_snap_workflow_daily_v1
        ON warehouse.snap_workflow_daily_v1(snapshot_date, snapshot_type, section_code, metric_code)
    """)


def build_snapshot(cur) -> int:
    cur.execute("""
        INSERT INTO warehouse.snap_workflow_daily_v1 (
            snapshot_date,
            snapshot_type,
            section_code,
            metric_code,
            metric_value,
            health_score,
            health_light,
            health_icon,
            health_reason_code,
            candidate_id,
            workflow_run_id,
            mart_version,
            snapshot_version,
            source_table,
            calculated_at,
            payload,
            created_at
        )
        SELECT
            current_date AS snapshot_date,
            'READ_ONLY_SYSTEM_STATUS' AS snapshot_type,
            d.section_code,
            d.metric_code,
            d.metric_value,
            d.health_score,
            d.health_light,
            d.health_icon,
            d.health_reason_code,
            c.candidate_id,
            c.workflow_run_id,
            d.mart_version,
            %s AS snapshot_version,
            'warehouse.mart_workflow_dashboard_v1' AS source_table,
            now(),
            jsonb_build_object(
                'source','WORKFLOW_SNAPSHOT_BUILDER_V1',
                'snapshot_policy','DAILY_RECALCULABLE_IDEMPOTENT',
                'presentation_source','READ_ONLY_SYSTEM_STATUS_UI_V1',
                'mart_only',true,
                'runtime_changed',false,
                'execution_changed',false,
                'orders_changed',false,
                'fills_changed',false,
                'micro_live_allowed',false
            ),
            now()
        FROM warehouse.mart_workflow_dashboard_v1 d
        LEFT JOIN LATERAL (
            SELECT candidate_id, workflow_run_id
            FROM warehouse.mart_candidate_workflow_v1
            ORDER BY updated_at DESC
            LIMIT 1
        ) c ON true
        ON CONFLICT(snapshot_date, snapshot_type, section_code, metric_code)
        DO UPDATE SET
            metric_value=EXCLUDED.metric_value,
            health_score=EXCLUDED.health_score,
            health_light=EXCLUDED.health_light,
            health_icon=EXCLUDED.health_icon,
            health_reason_code=EXCLUDED.health_reason_code,
            candidate_id=EXCLUDED.candidate_id,
            workflow_run_id=EXCLUDED.workflow_run_id,
            mart_version=EXCLUDED.mart_version,
            snapshot_version=EXCLUDED.snapshot_version,
            source_table=EXCLUDED.source_table,
            calculated_at=now(),
            payload=EXCLUDED.payload
    """, (SNAPSHOT_VERSION,))
    return int(cur.rowcount)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            ensure_schema(cur)

            if args.save:
                snapshot_rows = build_snapshot(cur)
                conn.commit()
            else:
                snapshot_rows = 0
                conn.rollback()

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM warehouse.snap_workflow_daily_v1
                WHERE snapshot_date=current_date
                  AND snapshot_type='READ_ONLY_SYSTEM_STATUS'
            """)
            today_total = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT section_code, metric_code, metric_value, health_light, health_icon
                FROM warehouse.snap_workflow_daily_v1
                WHERE snapshot_date=current_date
                  AND snapshot_type='READ_ONLY_SYSTEM_STATUS'
                ORDER BY section_code, metric_code
            """)
            rows = cur.fetchall()

    print("=== WORKFLOW_SNAPSHOT_BUILDER_V1 ===")
    print(f"mode={'save' if args.save else 'dry_run'}")
    print(f"snapshot_rows_changed={snapshot_rows}")
    print(f"snapshot_today_total={today_total}")

    for r in rows:
        print(
            "snapshot_row="
            f"{r['section_code']}|"
            f"{r['metric_code']}|"
            f"{r['metric_value']}|"
            f"{r['health_light']}|"
            f"{r['health_icon']}"
        )

    print("snapshot_policy=DAILY_RECALCULABLE_IDEMPOTENT")
    print("source_policy=MART_ONLY")
    print("presentation_policy=READS_MART_OR_SNAPSHOT_ONLY")
    print("read_only_ui_snapshot_ready=1")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=WORKFLOW_SNAPSHOT_BUILDER_V1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
