from __future__ import annotations
from marketcore.presentation.render_tree.v2 import ActionKindV2,RenderActionV2,RenderContentV2,RenderDocumentV2,RenderNodeStateV2,RenderNodeTypeV2,RenderNodeV2,validate_render_document_v2
from marketcore.presentation.workspace_v2.domain.research_snapshot_v2 import ResearchSnapshotV2

def _leaf(t,i,*,key=None,args=None,value=None,fmt=None,level=None):
    return RenderNodeV2(t,i,content=RenderContentV2(message_key=key,message_args=args,value=value,format_code=fmt,level_code=level))
def _metric(code,value,fmt="INTEGER"):
    return RenderNodeV2(RenderNodeTypeV2.METRIC_ROW,f"research.metric.{code}",children=(_leaf(RenderNodeTypeV2.METRIC_LABEL,f"research.metric.{code}.label",key=f"research.metric.{code}"),_leaf(RenderNodeTypeV2.METRIC_VALUE,f"research.metric.{code}.value",value=value,fmt=fmt)))

def _domain_key(value):
    code = str(value or "NO_DATA").strip().lower().replace(":", ".")
    return f"research.domain.{code}"

def _domain(t, node_id, value):
    key = _domain_key(value)
    return _leaf(t, node_id, key=key, args={"tooltip_key": f"{key}.tooltip"})

def _tile(code, value, status):
    return RenderNodeV2(
        RenderNodeTypeV2.CARD,
        f"research.tile.{code}",
        state=RenderNodeStateV2(status_code=status),
        children=(
            _leaf(RenderNodeTypeV2.TITLE, f"research.tile.{code}.title", key=f"research.tile.{code}"),
            _leaf(RenderNodeTypeV2.METRIC_VALUE, f"research.tile.{code}.value", value=value, fmt="INTEGER"),
        ),
    )

def _algorithm_table(items):
    columns=("algorithm","markets","variants","folds","pf","passes","status","reason")
    header=RenderNodeV2(RenderNodeTypeV2.TABLE_ROW,"research.algorithms.header",children=tuple(_leaf(RenderNodeTypeV2.TABLE_HEADER_CELL,f"research.algorithms.header.{code}",key=f"research.algorithm.column.{code}") for code in columns))
    rows=[]
    for index,item in enumerate(items,start=1):
        rows.append(RenderNodeV2(RenderNodeTypeV2.TABLE_ROW,f"research.algorithm.{index}",children=(
            _domain(RenderNodeTypeV2.TABLE_CELL,f"research.algorithm.{index}.family",item.family),
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.algorithm.{index}.markets",value=item.markets,fmt="INTEGER"),
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.algorithm.{index}.variants",value=item.variants,fmt="INTEGER"),
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.algorithm.{index}.folds",key="research.algorithm.folds",args={"passed":item.best_folds,"total":item.folds_total}),
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.algorithm.{index}.pf",value=item.best_profit_factor,fmt="DECIMAL"),
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.algorithm.{index}.passes",value=item.passes,fmt="INTEGER"),
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.algorithm.{index}.status",key=f"research.algorithm.status.{item.status.lower()}"),
            _domain(RenderNodeTypeV2.TABLE_CELL,f"research.algorithm.{index}.reason",item.fail_reason),
        )))
    return RenderNodeV2(RenderNodeTypeV2.TABLE,"research.algorithms.table",children=(RenderNodeV2(RenderNodeTypeV2.TABLE_HEAD,"research.algorithms.head",children=(header,)),RenderNodeV2(RenderNodeTypeV2.TABLE_BODY,"research.algorithms.body",children=tuple(rows))))

def _run_audit_table(items):
    columns=("status","started","steps","duration","outcome","reason","recommendation","analysis")
    header=RenderNodeV2(RenderNodeTypeV2.TABLE_ROW,"research.audit.header",children=tuple(_leaf(RenderNodeTypeV2.TABLE_HEADER_CELL,f"research.audit.header.{code}",key=f"research.audit.column.{code}") for code in columns))
    rows=[]
    for index,item in enumerate(items,start=1):
        rows.append(RenderNodeV2(RenderNodeTypeV2.TABLE_ROW,f"research.audit.{index}",children=(
            _domain(RenderNodeTypeV2.TABLE_CELL,f"research.audit.{index}.status",item.status),
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.audit.{index}.started",value=item.started_at,fmt="DATETIME"),
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.audit.{index}.steps",key="research.audit.steps",args={"completed":item.steps_completed,"total":item.steps_total}),
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.audit.{index}.duration",value=item.duration_seconds,fmt="INTEGER"),
            _domain(RenderNodeTypeV2.TABLE_CELL,f"research.audit.{index}.outcome",item.outcome),
            _domain(RenderNodeTypeV2.TABLE_CELL,f"research.audit.{index}.reason",item.reason),
            _domain(RenderNodeTypeV2.TABLE_CELL,f"research.audit.{index}.recommendation",item.recommendation),
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.audit.{index}.analysis",value=item.explanation),
        ),action=RenderActionV2(
            "research.edge_search.run",ActionKindV2.COMMAND,
            command_code="RESEARCH.RUN_EDGE_SEARCH",policy_class="RESEARCH_MAINTENANCE",
            reversible=True,rollback_code="RESEARCH.CANCEL_PENDING_REQUEST",
            idempotency_key="client.request",
        )))
    return RenderNodeV2(RenderNodeTypeV2.TABLE,"research.audit.table",children=(RenderNodeV2(RenderNodeTypeV2.TABLE_HEAD,"research.audit.head",children=(header,)),RenderNodeV2(RenderNodeTypeV2.TABLE_BODY,"research.audit.body",children=tuple(rows))))

def render_research_domain_v2(s: ResearchSnapshotV2, *, timezone_code="Europe/Moscow"):
    times=[x for x in (s.last_cycle_at,s.summary_refreshed_at,s.queue_updated_at,s.oos_updated_at) if x]
    source_as_of=min(times) if times else s.generated_at
    tiles=(
        _tile("instruments",s.active_symbols,"OK" if s.active_symbols else "WARNING"),
        _tile("errors",s.failed_symbols,"BLOCKED" if s.failed_symbols else "OK"),
        _tile("candidates",s.candidates,"OK" if s.candidates else "WARNING"),
        _tile("oos_pass",s.oos_pass_total,"OK" if s.oos_pass_total else "WARNING"),
        _tile("paper_ready",s.paper_ready,"OK" if s.paper_ready else "WARNING"),
        _tile("queue",s.queue_pending,"WARNING" if s.queue_pending else "OK"),
        _tile("markets",s.edge_search_markets,"OK" if s.edge_search_markets else "WARNING"),
        _tile("variants",s.edge_search_combinations,"OK" if s.edge_search_combinations else "WARNING"),
        _tile("pass",s.edge_search_pass,"OK" if s.edge_search_pass else "WARNING"),
        _tile("progress",s.edge_search_progress_pct,"OK" if s.edge_search_progress_pct >= 100 else "WARNING"),
    )
    refresh=RenderNodeV2(RenderNodeTypeV2.ACTION,"research.action.refresh",content=RenderContentV2(message_key="research.action.request_refresh"),action=RenderActionV2("research.request.refresh",ActionKindV2.COMMAND,command_code="RESEARCH.REQUEST_REFRESH",policy_class="RESEARCH_MAINTENANCE",reversible=True,rollback_code="RESEARCH.CANCEL_PENDING_REQUEST",idempotency_key="client.request"))
    edge_search=RenderNodeV2(RenderNodeTypeV2.ACTION,"research.action.edge_search",content=RenderContentV2(message_key="research.action.run_edge_search"),action=RenderActionV2("research.edge_search.run",ActionKindV2.COMMAND,command_code="RESEARCH.RUN_EDGE_SEARCH",policy_class="RESEARCH_MAINTENANCE",reversible=True,rollback_code="RESEARCH.CANCEL_PENDING_REQUEST",idempotency_key="client.request"))
    d=RenderDocumentV2(document_id="operator.research.v2",locale_code="ru-RU",fallback_locale_code="ru-RU",timezone_code=timezone_code,generated_at=s.generated_at,source_as_of=source_as_of,quality_code="MIXED_FRESHNESS",root=RenderNodeV2(RenderNodeTypeV2.WORKSPACE,"workspace.research",children=(RenderNodeV2(RenderNodeTypeV2.PAGE,"page.research",state=RenderNodeStateV2(status_code="WARNING",quality_code="MIXED_FRESHNESS"),children=(_leaf(RenderNodeTypeV2.TITLE,"research.title",key="research.workspace.title",level="PAGE"),_leaf(RenderNodeTypeV2.SUBTITLE,"research.subtitle",key="research.workspace.subtitle"),RenderNodeV2(RenderNodeTypeV2.GRID,"research.tiles",children=tiles),_leaf(RenderNodeTypeV2.TITLE,"research.audit.title",key="research.audit.title",level="SECTION"),_run_audit_table(s.edge_search_runs),_leaf(RenderNodeTypeV2.TITLE,"research.algorithms.title",key="research.algorithms.title",level="SECTION"),_algorithm_table(s.algorithm_results))),)))
    validate_render_document_v2(d); return d
