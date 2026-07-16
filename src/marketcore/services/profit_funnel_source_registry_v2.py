from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping

import psycopg2

from marketcore.core.profit_funnel_contract_v2 import ProfitFunnelStageV2


@dataclass(frozen=True, slots=True)
class ProfitFunnelSourceDefinitionV2:
    stage: ProfitFunnelStageV2
    source_identity: str
    sql: str
    scope_explicit: bool = False


@dataclass(frozen=True, slots=True)
class ProfitFunnelSourceObservationV2:
    stage: ProfitFunnelStageV2
    source_identity: str
    count: int
    source_as_of: datetime | None
    net_pnl: Decimal | None
    cost_impact: Decimal | None
    cohort_id: str | None
    cohort_count: int
    scope_code: str
    quality_code: str


_SOURCES: Mapping[ProfitFunnelStageV2, ProfitFunnelSourceDefinitionV2] = MappingProxyType({
    ProfitFunnelStageV2.RESEARCH: ProfitFunnelSourceDefinitionV2(
        ProfitFunnelStageV2.RESEARCH, "analytics.edge_discovery_run_v1.latest_done",
        "SELECT observations_scanned,finished_at,NULL::numeric,NULL::numeric,discovery_batch_id,1 FROM analytics.edge_discovery_run_v1 WHERE status_code='DONE' ORDER BY id DESC LIMIT 1",
    ),
    ProfitFunnelStageV2.CANDIDATE: ProfitFunnelSourceDefinitionV2(
        ProfitFunnelStageV2.CANDIDATE, "analytics.edge_candidate_v1",
        "SELECT count(*),max(updated_at),NULL::numeric,NULL::numeric,max(discovery_batch_id),count(DISTINCT discovery_batch_id) FROM analytics.edge_candidate_v1",
    ),
    ProfitFunnelStageV2.VALIDATED_EDGE: ProfitFunnelSourceDefinitionV2(
        ProfitFunnelStageV2.VALIDATED_EDGE, "analytics.profit_funnel_validated_edge_v2",
        "SELECT count(*),max(validated_at),NULL::numeric,NULL::numeric,max(discovery_batch_id),count(DISTINCT discovery_batch_id) FROM analytics.profit_funnel_validated_edge_v2",
    ),
    ProfitFunnelStageV2.OOS: ProfitFunnelSourceDefinitionV2(
        ProfitFunnelStageV2.OOS, "analytics.edge_oos_result_v1",
        "SELECT count(*),max(o.updated_at),NULL::numeric,NULL::numeric,max(c.discovery_batch_id),count(DISTINCT c.discovery_batch_id) FROM analytics.edge_oos_result_v1 o JOIN analytics.edge_candidate_v1 c ON c.observation_uuid=o.observation_uuid",
    ),
    ProfitFunnelStageV2.FORWARD: ProfitFunnelSourceDefinitionV2(
        ProfitFunnelStageV2.FORWARD, "analytics.forward_edge_observation_v1",
        "SELECT count(*),max(coalesce(exit_ts,entry_ts,signal_ts,created_at)),sum(net_pnl),sum(coalesce(commission,0)+coalesce(spread_cost,0)+coalesce(slippage,0)),max(cohort_id::text),count(DISTINCT cohort_id) FROM analytics.forward_edge_observation_v1",
    ),
    ProfitFunnelStageV2.SHADOW: ProfitFunnelSourceDefinitionV2(
        ProfitFunnelStageV2.SHADOW, "analytics.forward_edge_shadow_trade_v1",
        "SELECT count(*),max(updated_at),sum(net_pnl),sum(coalesce(commission,0)+coalesce(spread_cost,0)+coalesce(slippage,0)),max(cohort_id::text),count(DISTINCT cohort_id) FROM analytics.forward_edge_shadow_trade_v1",
    ),
    ProfitFunnelStageV2.PAPER: ProfitFunnelSourceDefinitionV2(
        ProfitFunnelStageV2.PAPER, "analytics.paper_runtime_candidate_v1.active_oos_pass",
        "SELECT count(*),max(p.updated_at),NULL::numeric,NULL::numeric,max(c.discovery_batch_id),count(DISTINCT c.discovery_batch_id) FROM analytics.paper_runtime_candidate_v1 p JOIN analytics.edge_candidate_v1 c USING(observation_uuid) WHERE p.paper_status='ACTIVE' AND c.candidate_status='OOS_PASS' AND c.paper_allowed",
    ),
    ProfitFunnelStageV2.RUNTIME: ProfitFunnelSourceDefinitionV2(
        ProfitFunnelStageV2.RUNTIME, "public.runtime_observations.latest_state",
        "SELECT count(*) FILTER (WHERE allow_runtime),max(observed_at) FILTER (WHERE allow_runtime),NULL::numeric,NULL::numeric,NULL::text,0 FROM (SELECT DISTINCT ON (symbol,strategy,timeframe) * FROM public.runtime_observations ORDER BY symbol,strategy,timeframe,observed_at DESC) latest",
    ),
    ProfitFunnelStageV2.LIVE: ProfitFunnelSourceDefinitionV2(
        ProfitFunnelStageV2.LIVE, "public.orders.exchange_accepted",
        "SELECT count(*) FILTER (WHERE exchange_order_id IS NOT NULL),max(created_ts) FILTER (WHERE exchange_order_id IS NOT NULL),NULL::numeric,NULL::numeric,NULL::text,0 FROM public.orders",
        scope_explicit=True,
    ),
    ProfitFunnelStageV2.PROFIT: ProfitFunnelSourceDefinitionV2(
        ProfitFunnelStageV2.PROFIT, "analytics.profit_factory_profit_fact_v1[data_scope=REAL]",
        "SELECT count(*),max(created_at),sum(realized_profit),NULL::numeric,NULL::text,0 FROM analytics.profit_factory_profit_fact_v1 WHERE data_scope='REAL'",
        scope_explicit=True,
    ),
})


def profit_funnel_source_definitions_v2() -> tuple[ProfitFunnelSourceDefinitionV2, ...]:
    return tuple(_SOURCES[stage] for stage in ProfitFunnelStageV2)


def observe_profit_funnel_sources_v2(dsn: str = "postgresql:///finam_core") -> tuple[ProfitFunnelSourceObservationV2, ...]:
    observations = []
    with psycopg2.connect(dsn) as connection:
        with connection.cursor() as cursor:
            for definition in profit_funnel_source_definitions_v2():
                cursor.execute(definition.sql)
                count, source_as_of, net_pnl, cost_impact, cohort_id, cohort_count = cursor.fetchone()
                cohort_count = int(cohort_count or 0)
                quality = (
                    "VERIFIED" if definition.scope_explicit and source_as_of is not None
                    else "UNAVAILABLE" if source_as_of is None
                    else "UNVERIFIED"
                )
                observations.append(ProfitFunnelSourceObservationV2(
                    definition.stage, definition.source_identity, int(count or 0), source_as_of,
                    Decimal(str(net_pnl)) if net_pnl is not None else None,
                    Decimal(str(cost_impact)) if cost_impact is not None else None,
                    str(cohort_id) if cohort_id is not None else None, cohort_count,
                    "REAL" if definition.scope_explicit else "SCOPE_UNVERIFIED", quality,
                ))
    return tuple(observations)
