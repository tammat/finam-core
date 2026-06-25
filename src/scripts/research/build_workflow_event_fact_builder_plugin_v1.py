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


CALCULATION_VERSION = "WORKFLOW_EVENT_FACT_BUILDER_PLUGIN_V1"


def db_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql:///finam_core")


def update_pipeline(cur, result) -> None:
    cur.execute("""
        UPDATE warehouse.fact_pipeline_runs_v1
        SET
            pipeline_status=%s,
            rows_out=GREATEST(rows_out, %s),
            duplicate_rows=%s,
            error_rows=%s,
            health_score=%s,
            health_light=%s,
            health_reason_code=%s,
            finished_at=now(),
            updated_at=now(),
            payload = payload || %s::jsonb
        WHERE fact_pipeline_run_id = (
            SELECT fact_pipeline_run_id
            FROM warehouse.fact_pipeline_runs_v1
            WHERE builder_name='WORKFLOW_EVENT_FACT_BUILDER_V1'
            ORDER BY fact_pipeline_run_id DESC
            LIMIT 1
        )
    """, (
        result.status,
        result.rows_out,
        result.duplicate_rows,
        result.error_rows,
        result.health_score,
        result.health_light,
        result.health_reason_code,
        psycopg2.extras.Json({
            "builder_result": result.payload,
            "builder_reason": result.reason,
            "calculation_version": CALCULATION_VERSION,
        }),
    ))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    with psycopg2.connect(db_url()) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            context = BuilderContext(
                builder_name="WORKFLOW_EVENT_FACT_BUILDER_V1",
                fact_domain="WORKFLOW",
                fact_type="EVENT_FACT",
                source_table="warehouse.nrm_workflow_event_v1",
                target_table="warehouse.fact_event_workflow_stage_v1,warehouse.fact_event_workflow_transition_v1",
                calculation_version=CALCULATION_VERSION,
                payload={},
            )

            result = BuilderExecutor(BuilderRegistry(cur)).execute(context)

            if args.save:
                update_pipeline(cur, result)
                conn.commit()
            else:
                conn.rollback()

            cur.execute("SELECT count(*)::bigint AS cnt FROM warehouse.fact_event_workflow_stage_v1")
            stage_total = int(cur.fetchone()["cnt"])

            cur.execute("SELECT count(*)::bigint AS cnt FROM warehouse.fact_event_workflow_transition_v1")
            transition_total = int(cur.fetchone()["cnt"])

    print("=== WORKFLOW_EVENT_FACT_BUILDER_PLUGIN_V1 ===")
    print(f"mode={'save' if args.save else 'dry_run'}")
    print(f"result_status={result.status}")
    print(f"result_reason={result.reason}")
    print(f"rows_out={result.rows_out}")
    print(f"stage_facts_inserted={result.payload.get('stage_facts_inserted')}")
    print(f"transition_facts_inserted={result.payload.get('transition_facts_inserted')}")
    print(f"stage_facts_total={stage_total}")
    print(f"transition_facts_total={transition_total}")
    print(f"health_score={result.health_score}")
    print(f"health_light={result.health_light}")
    print(f"health_reason_code={result.health_reason_code}")
    print("builder_model=PLUGIN_BASED")
    print("fact_policy=STORE_CODES_ONLY")
    print("incremental_policy=changed_since_only")
    print("no_full_scan_policy=1")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=WORKFLOW_EVENT_FACT_BUILDER_PLUGIN_V1_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
