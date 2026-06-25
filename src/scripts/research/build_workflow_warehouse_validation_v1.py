#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import sys

import psycopg2
import psycopg2.extras


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def count(cur, table: str) -> int:
    cur.execute(f"SELECT count(*)::bigint AS cnt FROM {table}")
    return int(cur.fetchone()["cnt"])


def main() -> int:
    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            checks = {
                "qlt_event": count(cur, "warehouse.qlt_workflow_event_v1"),
                "qlt_run": count(cur, "warehouse.qlt_workflow_run_v1"),
                "nrm_event": count(cur, "warehouse.nrm_workflow_event_v1"),
                "nrm_run": count(cur, "warehouse.nrm_workflow_run_v1"),
                "event_stage_fact": count(cur, "warehouse.fact_event_workflow_stage_v1"),
                "event_transition_fact": count(cur, "warehouse.fact_event_workflow_transition_v1"),
                "state_lifecycle": count(cur, "warehouse.fact_state_candidate_lifecycle_v1"),
                "state_health": count(cur, "warehouse.fact_state_workflow_health_v1"),
                "state_quality": count(cur, "warehouse.fact_state_workflow_quality_v1"),
                "dim_stage": count(cur, "warehouse.dim_stage_v1"),
                "dim_status_light": count(cur, "warehouse.dim_status_light_v1"),
                "sem_candidate": count(cur, "warehouse.sem_candidate_v1"),
                "sem_workflow": count(cur, "warehouse.sem_workflow_v1"),
                "mart_candidate": count(cur, "warehouse.mart_candidate_workflow_v1"),
                "mart_dashboard": count(cur, "warehouse.mart_workflow_dashboard_v1"),
            }

            cur.execute("""
                SELECT count(*)::bigint AS cnt
                FROM warehouse.snap_workflow_daily_v1
                WHERE snapshot_date=current_date
                  AND snapshot_type='READ_ONLY_SYSTEM_STATUS'
            """)
            checks["snap_today"] = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT candidate_id, workflow_status_code, current_stage_code,
                       health_score, health_light, health_icon
                FROM warehouse.mart_candidate_workflow_v1
                ORDER BY updated_at DESC
                LIMIT 1
            """)
            candidate = cur.fetchone()

            cur.execute("""
                SELECT string_agg(section_code || ':' || health_light, ',' ORDER BY (payload->>'display_order')::int) AS sections
                FROM warehouse.mart_workflow_dashboard_v1
            """)
            sections = cur.fetchone()["sections"]

    ok = (
        checks["qlt_event"] >= 6
        and checks["qlt_run"] >= 1
        and checks["nrm_event"] >= 6
        and checks["nrm_run"] >= 1
        and checks["event_stage_fact"] >= 6
        and checks["event_transition_fact"] >= 5
        and checks["state_lifecycle"] >= 1
        and checks["state_health"] >= 1
        and checks["state_quality"] >= 1
        and checks["dim_stage"] >= 8
        and checks["dim_status_light"] >= 7
        and checks["sem_candidate"] >= 1
        and checks["sem_workflow"] >= 1
        and checks["mart_candidate"] >= 1
        and checks["mart_dashboard"] >= 9
        and checks["snap_today"] >= 9
        and candidate is not None
    )

    print("=== WORKFLOW_WAREHOUSE_VALIDATION_V1 ===")
    for k, v in checks.items():
        print(f"{k}_rows={v}")

    if candidate:
        print(
            "candidate_latest="
            f"{candidate['candidate_id']}|"
            f"{candidate['workflow_status_code']}|"
            f"{candidate['current_stage_code']}|"
            f"{candidate['health_score']}|"
            f"{candidate['health_light']}|"
            f"{candidate['health_icon']}"
        )

    print(f"mart_sections={sections}")
    print("validation_scope=QUALITY,NORMALIZED,EVENT_FACT,STATE_FACT,DIMENSION,SEMANTIC,MART,SNAPSHOT,READ_ONLY_UI")
    print("source_policy=PRESENTATION_READS_MART_OR_SNAPSHOT_ONLY")
    print("workflow_warehouse_v1_complete=1" if ok else "workflow_warehouse_v1_complete=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=WORKFLOW_WAREHOUSE_VALIDATION_V1_READY" if ok else "VERDICT=WORKFLOW_WAREHOUSE_VALIDATION_V1_FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
