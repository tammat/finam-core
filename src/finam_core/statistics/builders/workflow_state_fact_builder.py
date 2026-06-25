# -*- coding: utf-8 -*-
from __future__ import annotations

from finam_core.statistics.builders.base_builder import FactBuilder
from finam_core.statistics.pipeline.builder_context import BuilderContext
from finam_core.statistics.pipeline.builder_result import BuilderResult


class WorkflowStateFactBuilder(FactBuilder):
    def __init__(self, cur) -> None:
        self.cur = cur

    def build(self, context: BuilderContext) -> BuilderResult:
        self.cur.execute("""
            INSERT INTO warehouse.fact_state_candidate_lifecycle_v1 (
                candidate_id, workflow_run_id, broker_id, exchange_id, market_code,
                instrument_id, symbol, display_symbol, asset_class_code, currency_code,
                timezone, strategy_code, timeframe, session_code,
                research_status_code, workflow_status_code, paper_status_code,
                current_stage_code, next_stage_code, status_code, reason_code,
                health_score, health_light, health_reason_code,
                event_ts, source_table, source_id, source_run_id,
                calculation_version, calculated_at, payload, updated_at
            )
            SELECT
                n.candidate_id, n.workflow_run_id, n.broker_id, n.exchange_id, n.market_code,
                n.instrument_id, n.symbol, n.display_symbol, n.asset_class_code, n.currency_code,
                n.timezone, n.strategy_code, n.timeframe, n.session_code,
                'UNKNOWN', n.status_code, 'NOT_STARTED',
                n.stage_code, NULL, n.status_code, n.reason_code,
                CASE WHEN n.status_code IN ('RUNNING','COMPLETED','OK') THEN 100 ELSE 70 END,
                CASE WHEN n.status_code IN ('RUNNING','COMPLETED','OK') THEN 'GREEN' ELSE 'YELLOW' END,
                CASE WHEN n.status_code IN ('RUNNING','COMPLETED','OK') THEN 'OK' ELSE n.reason_code END,
                n.event_ts, n.source_table, n.source_id, n.source_run_id,
                %s, now(),
                jsonb_build_object('source','WORKFLOW_STATE_FACT_BUILDER_PLUGIN_V1'),
                now()
            FROM warehouse.nrm_workflow_run_v1 n
            ON CONFLICT(candidate_id) DO UPDATE SET
                workflow_run_id=EXCLUDED.workflow_run_id,
                workflow_status_code=EXCLUDED.workflow_status_code,
                paper_status_code=EXCLUDED.paper_status_code,
                current_stage_code=EXCLUDED.current_stage_code,
                next_stage_code=EXCLUDED.next_stage_code,
                status_code=EXCLUDED.status_code,
                reason_code=EXCLUDED.reason_code,
                health_score=EXCLUDED.health_score,
                health_light=EXCLUDED.health_light,
                health_reason_code=EXCLUDED.health_reason_code,
                event_ts=EXCLUDED.event_ts,
                source_table=EXCLUDED.source_table,
                source_id=EXCLUDED.source_id,
                source_run_id=EXCLUDED.source_run_id,
                calculation_version=EXCLUDED.calculation_version,
                calculated_at=now(),
                payload=EXCLUDED.payload,
                updated_at=now()
        """, (context.calculation_version,))
        lifecycle_rows = int(self.cur.rowcount)

        self.cur.execute("""
            INSERT INTO warehouse.fact_state_workflow_health_v1 (
                workflow_run_id, candidate_id, health_score, health_light,
                health_reason_code, status_code, reason_code, event_ts,
                source_table, source_id, source_run_id, calculation_version,
                calculated_at, payload, updated_at
            )
            SELECT
                n.workflow_run_id, n.candidate_id,
                CASE WHEN n.status_code IN ('RUNNING','COMPLETED','OK') THEN 100 ELSE 70 END,
                CASE WHEN n.status_code IN ('RUNNING','COMPLETED','OK') THEN 'GREEN' ELSE 'YELLOW' END,
                CASE WHEN n.status_code IN ('RUNNING','COMPLETED','OK') THEN 'OK' ELSE n.reason_code END,
                n.status_code, n.reason_code, n.event_ts,
                n.source_table, n.source_id, n.source_run_id,
                %s, now(),
                jsonb_build_object('source','WORKFLOW_STATE_FACT_BUILDER_PLUGIN_V1'),
                now()
            FROM warehouse.nrm_workflow_run_v1 n
            ON CONFLICT(workflow_run_id) DO UPDATE SET
                candidate_id=EXCLUDED.candidate_id,
                health_score=EXCLUDED.health_score,
                health_light=EXCLUDED.health_light,
                health_reason_code=EXCLUDED.health_reason_code,
                status_code=EXCLUDED.status_code,
                reason_code=EXCLUDED.reason_code,
                event_ts=EXCLUDED.event_ts,
                source_table=EXCLUDED.source_table,
                source_id=EXCLUDED.source_id,
                source_run_id=EXCLUDED.source_run_id,
                calculation_version=EXCLUDED.calculation_version,
                calculated_at=now(),
                payload=EXCLUDED.payload,
                updated_at=now()
        """, (context.calculation_version,))
        health_rows = int(self.cur.rowcount)

        self.cur.execute("""
            INSERT INTO warehouse.fact_state_workflow_quality_v1 (
                workflow_run_id, candidate_id, latency_ms, success_rate,
                wait_rate, block_rate, fail_rate, health_score, health_light,
                health_reason_code, status_code, reason_code, event_ts,
                source_table, source_id, source_run_id, calculation_version,
                calculated_at, payload, updated_at
            )
            WITH event_stats AS (
                SELECT
                    workflow_run_id,
                    count(*)::numeric AS total_events,
                    sum(CASE WHEN status_code IN ('OK','COMPLETED','RUNNING') THEN 1 ELSE 0 END)::numeric AS success_events,
                    min(event_ts) AS first_ts,
                    max(event_ts) AS last_ts
                FROM warehouse.nrm_workflow_event_v1
                GROUP BY workflow_run_id
            )
            SELECT
                n.workflow_run_id,
                n.candidate_id,
                EXTRACT(EPOCH FROM (s.last_ts - s.first_ts)) * 1000,
                CASE WHEN s.total_events > 0 THEN s.success_events / s.total_events ELSE NULL END,
                0, 0, 0,
                100, 'GREEN', 'OK',
                n.status_code, n.reason_code, n.event_ts,
                'warehouse.nrm_workflow_event_v1',
                n.source_id, n.source_run_id,
                %s, now(),
                jsonb_build_object(
                    'source','WORKFLOW_STATE_FACT_BUILDER_PLUGIN_V1',
                    'events_total', s.total_events
                ),
                now()
            FROM warehouse.nrm_workflow_run_v1 n
            LEFT JOIN event_stats s
              ON s.workflow_run_id=n.workflow_run_id
            ON CONFLICT(workflow_run_id) DO UPDATE SET
                candidate_id=EXCLUDED.candidate_id,
                latency_ms=EXCLUDED.latency_ms,
                success_rate=EXCLUDED.success_rate,
                wait_rate=EXCLUDED.wait_rate,
                block_rate=EXCLUDED.block_rate,
                fail_rate=EXCLUDED.fail_rate,
                health_score=EXCLUDED.health_score,
                health_light=EXCLUDED.health_light,
                health_reason_code=EXCLUDED.health_reason_code,
                status_code=EXCLUDED.status_code,
                reason_code=EXCLUDED.reason_code,
                event_ts=EXCLUDED.event_ts,
                source_table=EXCLUDED.source_table,
                source_id=EXCLUDED.source_id,
                source_run_id=EXCLUDED.source_run_id,
                calculation_version=EXCLUDED.calculation_version,
                calculated_at=now(),
                payload=EXCLUDED.payload,
                updated_at=now()
        """, (context.calculation_version,))
        quality_rows = int(self.cur.rowcount)

        rows_out = lifecycle_rows + health_rows + quality_rows

        return BuilderResult(
            status="COMPLETED",
            rows_in=0,
            rows_out=rows_out,
            duplicate_rows=0,
            error_rows=0,
            health_score=100,
            health_light="GREEN",
            health_reason_code="OK",
            reason="WORKFLOW_STATE_FACT_BUILDER_PLUGIN_OK",
            payload={
                "candidate_lifecycle_rows": lifecycle_rows,
                "workflow_health_rows": health_rows,
                "workflow_quality_rows": quality_rows,
            },
        )
