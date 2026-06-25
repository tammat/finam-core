# -*- coding: utf-8 -*-
from __future__ import annotations

import psycopg2.extras

from finam_core.statistics.builders.base_builder import FactBuilder
from finam_core.statistics.pipeline.builder_context import BuilderContext
from finam_core.statistics.pipeline.builder_result import BuilderResult


class WorkflowEventFactBuilder(FactBuilder):
    def __init__(self, cur) -> None:
        self.cur = cur

    def build(self, context: BuilderContext) -> BuilderResult:
        self.cur.execute("""
            INSERT INTO warehouse.fact_event_workflow_stage_v1 (
                workflow_run_id,candidate_id,broker_id,exchange_id,market_code,
                instrument_id,symbol,display_symbol,asset_class_code,currency_code,
                timezone,strategy_code,timeframe,session_code,stage_code,status_code,
                reason_code,result_status,stage_duration_ms,health_score,health_light,
                health_reason_code,event_ts,source_table,source_id,source_event_id,
                source_run_id,calculation_version,calculated_at,payload
            )
            SELECT
                n.workflow_run_id,n.candidate_id,n.broker_id,n.exchange_id,n.market_code,
                n.instrument_id,n.symbol,n.display_symbol,n.asset_class_code,n.currency_code,
                n.timezone,n.strategy_code,n.timeframe,n.session_code,n.stage_code,n.status_code,
                n.reason_code,n.status_code,NULL,
                CASE WHEN n.status_code='OK' THEN 100 ELSE 80 END,
                CASE WHEN n.status_code='OK' THEN 'GREEN' ELSE 'YELLOW' END,
                CASE WHEN n.status_code='OK' THEN 'OK' ELSE n.reason_code END,
                n.event_ts,n.source_table,n.source_id,n.source_event_id,n.workflow_run_id,
                %s,now(),
                jsonb_build_object(
                    'source','WORKFLOW_EVENT_FACT_BUILDER_PLUGIN_V1',
                    'fact_type','WORKFLOW_STAGE_EVENT',
                    'runtime_changed',false,
                    'execution_changed',false,
                    'orders_changed',false,
                    'fills_changed',false,
                    'micro_live_allowed',false
                )
            FROM warehouse.nrm_workflow_event_v1 n
            WHERE NOT EXISTS (
                SELECT 1
                FROM warehouse.fact_event_workflow_stage_v1 f
                WHERE f.source_event_id = n.source_event_id
            )
        """, (context.calculation_version,))
        stage_rows = int(self.cur.rowcount)

        self.cur.execute("""
            INSERT INTO warehouse.fact_event_workflow_transition_v1 (
                workflow_run_id,candidate_id,broker_id,exchange_id,market_code,
                instrument_id,symbol,display_symbol,asset_class_code,currency_code,
                timezone,strategy_code,timeframe,session_code,from_stage_code,to_stage_code,
                status_code,reason_code,transition_duration_ms,health_score,health_light,
                health_reason_code,event_ts,source_table,source_id,source_event_id,
                source_run_id,calculation_version,calculated_at,payload
            )
            SELECT
                n.workflow_run_id,n.candidate_id,n.broker_id,n.exchange_id,n.market_code,
                n.instrument_id,n.symbol,n.display_symbol,n.asset_class_code,n.currency_code,
                n.timezone,n.strategy_code,n.timeframe,n.session_code,
                e.stage_from,n.stage_code,
                n.status_code,n.reason_code,NULL,
                CASE WHEN n.status_code='OK' THEN 100 ELSE 80 END,
                CASE WHEN n.status_code='OK' THEN 'GREEN' ELSE 'YELLOW' END,
                CASE WHEN n.status_code='OK' THEN 'OK' ELSE n.reason_code END,
                n.event_ts,n.source_table,n.source_id,n.source_event_id,n.workflow_run_id,
                %s,now(),
                jsonb_build_object(
                    'source','WORKFLOW_EVENT_FACT_BUILDER_PLUGIN_V1',
                    'fact_type','WORKFLOW_TRANSITION_EVENT',
                    'runtime_changed',false,
                    'execution_changed',false,
                    'orders_changed',false,
                    'fills_changed',false,
                    'micro_live_allowed',false
                )
            FROM warehouse.nrm_workflow_event_v1 n
            JOIN research.workflow_runtime_events_v1 e
              ON e.event_id = n.source_event_id
            WHERE e.stage_from IS NOT NULL
              AND e.stage_to IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM warehouse.fact_event_workflow_transition_v1 f
                  WHERE f.source_event_id = n.source_event_id
              )
        """, (context.calculation_version,))
        transition_rows = int(self.cur.rowcount)

        rows_out = stage_rows + transition_rows

        return BuilderResult(
            status="COMPLETED",
            rows_in=0,
            rows_out=rows_out,
            duplicate_rows=0,
            error_rows=0,
            health_score=100,
            health_light="GREEN",
            health_reason_code="OK",
            reason="WORKFLOW_EVENT_FACT_BUILDER_PLUGIN_OK",
            payload={
                "stage_facts_inserted": stage_rows,
                "transition_facts_inserted": transition_rows,
            },
        )
