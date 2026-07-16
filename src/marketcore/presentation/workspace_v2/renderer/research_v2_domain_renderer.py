from __future__ import annotations
from marketcore.presentation.render_tree.v2 import ActionKindV2,RenderActionV2,RenderContentV2,RenderDocumentV2,RenderNodeStateV2,RenderNodeTypeV2,RenderNodeV2,validate_render_document_v2
from marketcore.presentation.workspace_v2.domain.research_snapshot_v2 import ResearchSnapshotV2

def _leaf(t,i,*,key=None,value=None,fmt=None,level=None):
    return RenderNodeV2(t,i,content=RenderContentV2(message_key=key,value=value,format_code=fmt,level_code=level))
def _metric(code,value,fmt="INTEGER"):
    return RenderNodeV2(RenderNodeTypeV2.METRIC_ROW,f"research.metric.{code}",children=(_leaf(RenderNodeTypeV2.METRIC_LABEL,f"research.metric.{code}.label",key=f"research.metric.{code}"),_leaf(RenderNodeTypeV2.METRIC_VALUE,f"research.metric.{code}.value",value=value,fmt=fmt)))

def render_research_domain_v2(s: ResearchSnapshotV2, *, timezone_code="Europe/Moscow"):
    times=[x for x in (s.last_cycle_at,s.summary_refreshed_at,s.queue_updated_at,s.oos_updated_at) if x]
    source_as_of=min(times) if times else s.generated_at
    metrics=(
        _metric("supervisor_status",s.supervisor_status,"DOMAIN_CODE"),_metric("active_symbols",s.active_symbols),_metric("failed_symbols",s.failed_symbols),
        _metric("candidates",s.candidates),_metric("summary_oos_pass",s.oos_pass),_metric("paper_ready",s.paper_ready),
        _metric("queue_total",s.queue_total),_metric("queue_pending",s.queue_pending),_metric("queue_failed",s.queue_failed),
        _metric("oos_total",s.oos_total),_metric("oos_pass",s.oos_pass_total),
        _metric("edge_search_status",s.edge_search_status,"DOMAIN_CODE"),
        _metric("edge_search_step",s.edge_search_step,"DOMAIN_CODE"),
        _metric("edge_search_progress",s.edge_search_progress_pct,"PERCENT"),
        _metric("edge_search_markets",s.edge_search_markets),
        _metric("edge_search_combinations",s.edge_search_combinations),
        _metric("edge_search_pass",s.edge_search_pass),
    )
    refresh=RenderNodeV2(RenderNodeTypeV2.ACTION,"research.action.refresh",content=RenderContentV2(message_key="research.action.request_refresh"),action=RenderActionV2("research.request.refresh",ActionKindV2.COMMAND,command_code="RESEARCH.REQUEST_REFRESH",policy_class="RESEARCH_MAINTENANCE",reversible=True,rollback_code="RESEARCH.CANCEL_PENDING_REQUEST",idempotency_key="client.request"))
    edge_search=RenderNodeV2(RenderNodeTypeV2.ACTION,"research.action.edge_search",content=RenderContentV2(message_key="research.action.run_edge_search"),action=RenderActionV2("research.edge_search.run",ActionKindV2.COMMAND,command_code="RESEARCH.RUN_EDGE_SEARCH",policy_class="RESEARCH_MAINTENANCE",reversible=True,rollback_code="RESEARCH.CANCEL_PENDING_REQUEST",idempotency_key="client.request"))
    d=RenderDocumentV2(document_id="operator.research.v2",locale_code="ru-RU",fallback_locale_code="ru-RU",timezone_code=timezone_code,generated_at=s.generated_at,source_as_of=source_as_of,quality_code="MIXED_FRESHNESS",root=RenderNodeV2(RenderNodeTypeV2.WORKSPACE,"workspace.research",children=(RenderNodeV2(RenderNodeTypeV2.PAGE,"page.research",state=RenderNodeStateV2(status_code="WARNING",quality_code="MIXED_FRESHNESS"),children=(_leaf(RenderNodeTypeV2.TITLE,"research.title",key="research.workspace.title",level="PAGE"),_leaf(RenderNodeTypeV2.SUBTITLE,"research.subtitle",key="research.workspace.subtitle"),edge_search,refresh,RenderNodeV2(RenderNodeTypeV2.METRIC_LIST,"research.metrics",children=metrics))),)))
    validate_render_document_v2(d); return d
