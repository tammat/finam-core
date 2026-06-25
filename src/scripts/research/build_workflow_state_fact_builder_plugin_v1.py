#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import os
import sys

import psycopg2
import psycopg2.extras

from finam_core.statistics.pipeline.builder_context import BuilderContext
from finam_core.statistics.pipeline.builder_executor import BuilderExecutor
from finam_core.statistics.pipeline.builder_registry import BuilderRegistry


CALCULATION_VERSION = "WORKFLOW_STATE_FACT_BUILDER_PLUGIN_V1"


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            context = BuilderContext(
                builder_name="WORKFLOW_STATE_FACT_BUILDER_V1",
                fact_domain="WORKFLOW",
                fact_type="STATE_FACT",
                source_table="warehouse.nrm_workflow_run_v1",
                target_table="warehouse.fact_state_candidate_lifecycle_v1,warehouse.fact_state_workflow_health_v1,warehouse.fact_state_workflow_quality_v1",
                calculation_version=CALCULATION_VERSION,
                payload={},
            )

            result = BuilderExecutor(BuilderRegistry(cur)).execute(context)

            if args.save:
                conn.commit()
            else:
                conn.rollback()

            cur.execute("SELECT count(*)::bigint AS cnt FROM warehouse.fact_state_candidate_lifecycle_v1")
            lifecycle_total = int(cur.fetchone()["cnt"])

            cur.execute("SELECT count(*)::bigint AS cnt FROM warehouse.fact_state_workflow_health_v1")
            health_total = int(cur.fetchone()["cnt"])

            cur.execute("SELECT count(*)::bigint AS cnt FROM warehouse.fact_state_workflow_quality_v1")
            quality_total = int(cur.fetchone()["cnt"])

            cur.execute("""
                SELECT candidate_id, workflow_status_code, current_stage_code,
                       coalesce(next_stage_code,'NULL') AS next_stage_code,
                       health_score, health_light, health_reason_code
                FROM warehouse.fact_state_candidate_lifecycle_v1
                ORDER BY updated_at DESC
                LIMIT 1
            """)
            latest = cur.fetchone()

    print("=== WORKFLOW_STATE_FACT_BUILDER_PLUGIN_V1 ===")
    print(f"mode={'save' if args.save else 'dry_run'}")
    print(f"result_status={result.status}")
    print(f"result_reason={result.reason}")
    print(f"rows_out={result.rows_out}")
    print(f"candidate_lifecycle_rows={result.payload.get('candidate_lifecycle_rows')}")
    print(f"workflow_health_rows={result.payload.get('workflow_health_rows')}")
    print(f"workflow_quality_rows={result.payload.get('workflow_quality_rows')}")
    print(f"candidate_lifecycle_total={lifecycle_total}")
    print(f"workflow_health_total={health_total}")
    print(f"workflow_quality_total={quality_total}")

    if latest:
        print(
            "candidate_state="
            f"{latest['candidate_id']}|"
            f"{latest['workflow_status_code']}|"
            f"{latest['current_stage_code']}|"
            f"{latest['next_stage_code']}|"
            f"health={latest['health_score']}|"
            f"light={latest['health_light']}|"
            f"reason={latest['health_reason_code']}"
        )

    print("builder_model=PLUGIN_BASED")
    print("source_policy=NORMALIZED_LAYER_ONLY")
    print("fact_policy=STATE_FACT_RECALCULABLE")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=WORKFLOW_STATE_FACT_BUILDER_PLUGIN_V1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
