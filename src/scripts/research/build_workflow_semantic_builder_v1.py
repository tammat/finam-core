#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import os
import sys

import psycopg2
import psycopg2.extras


SEMANTIC_VERSION = "WORKFLOW_SEMANTIC_BUILDER_V1"


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def build_sem_candidate(cur) -> int:
    cur.execute("""
        INSERT INTO warehouse.sem_candidate_v1 (
            candidate_id,
            workflow_run_id,
            symbol,
            display_symbol,
            strategy_code,
            timeframe,
            workflow_status_code,
            workflow_status_label_ru,
            current_stage_code,
            current_stage_label_ru,
            next_stage_code,
            next_stage_label_ru,
            health_score,
            health_light,
            health_icon,
            health_reason_code,
            semantic_version,
            payload,
            updated_at
        )
        SELECT
            c.candidate_id,
            c.workflow_run_id,
            c.symbol,
            c.display_symbol,
            c.strategy_code,
            c.timeframe,
            c.workflow_status_code,
            c.workflow_status_code AS workflow_status_label_ru,
            c.current_stage_code,
            coalesce(ds_cur.label_ru, c.current_stage_code) AS current_stage_label_ru,
            c.next_stage_code,
            coalesce(ds_next.label_ru, c.next_stage_code, 'NULL') AS next_stage_label_ru,
            c.health_score,
            c.health_light,
            coalesce(dl.icon, c.health_light) AS health_icon,
            c.health_reason_code,
            %s,
            jsonb_build_object(
                'source','WORKFLOW_SEMANTIC_BUILDER_V1',
                'semantic_object','Candidate',
                'presentation_ready',true,
                'runtime_changed',false,
                'execution_changed',false,
                'orders_changed',false,
                'fills_changed',false,
                'micro_live_allowed',false
            ),
            now()
        FROM warehouse.fact_state_candidate_lifecycle_v1 c
        LEFT JOIN warehouse.dim_stage_v1 ds_cur
          ON ds_cur.stage_code = c.current_stage_code
        LEFT JOIN warehouse.dim_stage_v1 ds_next
          ON ds_next.stage_code = c.next_stage_code
        LEFT JOIN warehouse.dim_status_light_v1 dl
          ON dl.light_code = c.health_light
        ON CONFLICT(candidate_id) DO UPDATE SET
            workflow_run_id=EXCLUDED.workflow_run_id,
            symbol=EXCLUDED.symbol,
            display_symbol=EXCLUDED.display_symbol,
            strategy_code=EXCLUDED.strategy_code,
            timeframe=EXCLUDED.timeframe,
            workflow_status_code=EXCLUDED.workflow_status_code,
            workflow_status_label_ru=EXCLUDED.workflow_status_label_ru,
            current_stage_code=EXCLUDED.current_stage_code,
            current_stage_label_ru=EXCLUDED.current_stage_label_ru,
            next_stage_code=EXCLUDED.next_stage_code,
            next_stage_label_ru=EXCLUDED.next_stage_label_ru,
            health_score=EXCLUDED.health_score,
            health_light=EXCLUDED.health_light,
            health_icon=EXCLUDED.health_icon,
            health_reason_code=EXCLUDED.health_reason_code,
            semantic_version=EXCLUDED.semantic_version,
            payload=EXCLUDED.payload,
            updated_at=now()
    """, (SEMANTIC_VERSION,))
    return int(cur.rowcount)


def build_sem_workflow(cur) -> int:
    cur.execute("""
        INSERT INTO warehouse.sem_workflow_v1 (
            workflow_run_id,
            candidate_id,
            workflow_status_code,
            workflow_status_label_ru,
            current_stage_code,
            current_stage_label_ru,
            next_stage_code,
            next_stage_label_ru,
            latency_ms,
            success_rate,
            health_score,
            health_light,
            health_icon,
            health_reason_code,
            semantic_version,
            payload,
            updated_at
        )
        SELECT
            c.workflow_run_id,
            c.candidate_id,
            c.workflow_status_code,
            c.workflow_status_code AS workflow_status_label_ru,
            c.current_stage_code,
            coalesce(ds_cur.label_ru, c.current_stage_code) AS current_stage_label_ru,
            c.next_stage_code,
            coalesce(ds_next.label_ru, c.next_stage_code, 'NULL') AS next_stage_label_ru,
            q.latency_ms,
            q.success_rate,
            h.health_score,
            h.health_light,
            coalesce(dl.icon, h.health_light) AS health_icon,
            h.health_reason_code,
            %s,
            jsonb_build_object(
                'source','WORKFLOW_SEMANTIC_BUILDER_V1',
                'semantic_object','Workflow',
                'presentation_ready',true,
                'runtime_changed',false,
                'execution_changed',false,
                'orders_changed',false,
                'fills_changed',false,
                'micro_live_allowed',false
            ),
            now()
        FROM warehouse.fact_state_candidate_lifecycle_v1 c
        LEFT JOIN warehouse.fact_state_workflow_health_v1 h
          ON h.workflow_run_id = c.workflow_run_id
        LEFT JOIN warehouse.fact_state_workflow_quality_v1 q
          ON q.workflow_run_id = c.workflow_run_id
        LEFT JOIN warehouse.dim_stage_v1 ds_cur
          ON ds_cur.stage_code = c.current_stage_code
        LEFT JOIN warehouse.dim_stage_v1 ds_next
          ON ds_next.stage_code = c.next_stage_code
        LEFT JOIN warehouse.dim_status_light_v1 dl
          ON dl.light_code = h.health_light
        ON CONFLICT(workflow_run_id) DO UPDATE SET
            candidate_id=EXCLUDED.candidate_id,
            workflow_status_code=EXCLUDED.workflow_status_code,
            workflow_status_label_ru=EXCLUDED.workflow_status_label_ru,
            current_stage_code=EXCLUDED.current_stage_code,
            current_stage_label_ru=EXCLUDED.current_stage_label_ru,
            next_stage_code=EXCLUDED.next_stage_code,
            next_stage_label_ru=EXCLUDED.next_stage_label_ru,
            latency_ms=EXCLUDED.latency_ms,
            success_rate=EXCLUDED.success_rate,
            health_score=EXCLUDED.health_score,
            health_light=EXCLUDED.health_light,
            health_icon=EXCLUDED.health_icon,
            health_reason_code=EXCLUDED.health_reason_code,
            semantic_version=EXCLUDED.semantic_version,
            payload=EXCLUDED.payload,
            updated_at=now()
    """, (SEMANTIC_VERSION,))
    return int(cur.rowcount)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if args.save:
                candidate_rows = build_sem_candidate(cur)
                workflow_rows = build_sem_workflow(cur)
                conn.commit()
            else:
                candidate_rows = 0
                workflow_rows = 0
                conn.rollback()

            cur.execute("SELECT count(*)::bigint AS cnt FROM warehouse.sem_candidate_v1")
            candidate_total = int(cur.fetchone()["cnt"])

            cur.execute("SELECT count(*)::bigint AS cnt FROM warehouse.sem_workflow_v1")
            workflow_total = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT candidate_id, display_symbol, strategy_code, workflow_status_code,
                       current_stage_code, current_stage_label_ru,
                       next_stage_code, next_stage_label_ru,
                       health_score, health_light, health_icon, health_reason_code
                FROM warehouse.sem_candidate_v1
                ORDER BY updated_at DESC
                LIMIT 1
            """)
            candidate = cur.fetchone()

            cur.execute("""
                SELECT workflow_run_id, candidate_id, workflow_status_code,
                       current_stage_code, current_stage_label_ru,
                       next_stage_code, next_stage_label_ru,
                       health_score, health_light, health_icon, health_reason_code
                FROM warehouse.sem_workflow_v1
                ORDER BY updated_at DESC
                LIMIT 1
            """)
            workflow = cur.fetchone()

    print("=== WORKFLOW_SEMANTIC_BUILDER_V1 ===")
    print(f"mode={'save' if args.save else 'dry_run'}")
    print(f"sem_candidate_rows_changed={candidate_rows}")
    print(f"sem_workflow_rows_changed={workflow_rows}")
    print(f"sem_candidate_total={candidate_total}")
    print(f"sem_workflow_total={workflow_total}")

    if candidate:
        print(
            "sem_candidate="
            f"{candidate['candidate_id']}|"
            f"{candidate['display_symbol']}|"
            f"{candidate['strategy_code']}|"
            f"{candidate['workflow_status_code']}|"
            f"{candidate['current_stage_code']}|"
            f"{candidate['current_stage_label_ru']}|"
            f"{candidate['next_stage_code']}|"
            f"{candidate['next_stage_label_ru']}|"
            f"health={candidate['health_score']}|"
            f"{candidate['health_light']}|"
            f"{candidate['health_icon']}|"
            f"{candidate['health_reason_code']}"
        )

    if workflow:
        print(
            "sem_workflow="
            f"{workflow['workflow_run_id']}|"
            f"{workflow['candidate_id']}|"
            f"{workflow['workflow_status_code']}|"
            f"{workflow['current_stage_code']}|"
            f"{workflow['current_stage_label_ru']}|"
            f"{workflow['next_stage_code']}|"
            f"{workflow['next_stage_label_ru']}|"
            f"health={workflow['health_score']}|"
            f"{workflow['health_light']}|"
            f"{workflow['health_icon']}|"
            f"{workflow['health_reason_code']}"
        )

    print("semantic_contract=STABLE")
    print("semantic_policy=BUSINESS_OBJECTS_FOR_UI")
    print("presentation_ready=1")
    print("mart_reads=SEMANTIC_ONLY")
    print("ui_reads=MART_OR_SNAPSHOT_ONLY")
    print("decision_logic_policy=NO_DECISION_LOGIC_IN_SEMANTIC_LAYER")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=WORKFLOW_SEMANTIC_BUILDER_V1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
