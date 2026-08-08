from __future__ import annotations
from marketcore.presentation.render_tree.v2 import ActionKindV2,RenderActionV2,RenderContentV2,RenderDocumentV2,RenderNodeStateV2,RenderNodeTypeV2,RenderNodeV2,validate_render_document_v2
from marketcore.presentation.workspace_v2.domain.research_snapshot_v2 import ResearchSnapshotV2
from marketcore.presentation.workspace_v2.resolver.ngu6_frozen_day_oos_status_v1 import resolve_ngu6_frozen_day_oos_status_v1

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

def _process_status(node_id, item):
    key = _domain_key(item.status)
    return _leaf(RenderNodeTypeV2.TABLE_CELL,node_id,key=key,args={
        "tooltip_key": f"{key}.tooltip",
        "progress_pct": item.progress_pct,
        "current_step": item.current_step,
    })

def _recommendation(node_id, item):
    key = _domain_key(item.recommendation)
    return _leaf(RenderNodeTypeV2.TABLE_CELL,node_id,key=key,args={
        "tooltip_key": f"{key}.tooltip",
        "process_id": item.process_id,
        "actions": list(item.available_actions),
    })

def _tile(code, value, status, status_key=None):
    status_key = status_key or {
        "OK": "research.tile.status.ready",
        "BLOCKED": "research.tile.status.blocked",
    }.get(status, "research.tile.status.attention")
    return RenderNodeV2(
        RenderNodeTypeV2.CARD,
        f"research.tile.{code}",
        state=RenderNodeStateV2(status_code=status),
        children=(
            _leaf(RenderNodeTypeV2.TITLE, f"research.tile.{code}.title", key=f"research.tile.{code}"),
            _leaf(RenderNodeTypeV2.METRIC_VALUE, f"research.tile.{code}.value", value=value, fmt="INTEGER"),
            _leaf(RenderNodeTypeV2.TEXT, f"research.tile.{code}.state", key=status_key,
                  args={"tooltip_key": f"{status_key}.tooltip"}),
        ),
    )

def _status_tile(code, value):
    status = "BLOCKED" if value == "FAILED" else "OK" if value == "HEALTHY" else "WARNING"
    return RenderNodeV2(RenderNodeTypeV2.CARD,f"research.tile.{code}",
        state=RenderNodeStateV2(status_code=status),children=(
            _leaf(RenderNodeTypeV2.TITLE,f"research.tile.{code}.title",key=f"research.tile.{code}"),
            _domain(RenderNodeTypeV2.METRIC_VALUE,f"research.tile.{code}.value",value),
        ))

def _validation_funnel_tiles(s):
    values=(
        ("validation_in_sample",s.validation_in_sample),
        ("validation_oos",s.validation_oos),
        ("validation_after_costs",s.validation_after_costs),
        ("validation_stable",s.validation_stable),
    )
    return RenderNodeV2(RenderNodeTypeV2.GRID,"research.validation_funnel.tiles",children=tuple(
        RenderNodeV2(RenderNodeTypeV2.CARD,f"research.tile.{code}",
            state=RenderNodeStateV2(status_code=("WARNING" if not s.validation_funnel_available else "OK" if value else "BLOCKED")),children=(
                _leaf(RenderNodeTypeV2.TITLE,f"research.tile.{code}.title",key=f"research.tile.{code}"),
                _leaf(RenderNodeTypeV2.METRIC_VALUE,f"research.tile.{code}.value",
                    value=value if s.validation_funnel_available else None,
                    fmt="INTEGER" if s.validation_funnel_available else None,
                    key=None if s.validation_funnel_available else "research.domain.no_data"),
            )) for code,value in values))

def _validation_funnel_recommendation(s):
    return RenderNodeV2(RenderNodeTypeV2.CARD,"research.validation_funnel.recommendation",
        state=RenderNodeStateV2(status_code="WARNING" if s.validation_funnel_available else "BLOCKED"),children=(
            _leaf(RenderNodeTypeV2.TITLE,"research.validation_funnel.recommendation.title",key="research.validation_funnel.recommendation.title"),
            RenderNodeV2(RenderNodeTypeV2.METRIC_ROW,"research.validation_funnel.recommendation.stage",children=(
                _leaf(RenderNodeTypeV2.METRIC_LABEL,"research.validation_funnel.recommendation.stage.label",key="research.validation_funnel.stage"),
                _leaf(RenderNodeTypeV2.METRIC_VALUE,"research.validation_funnel.recommendation.stage.value",key=f"research.funnel.stage.{s.validation_bottleneck_stage.lower()}" if s.validation_funnel_available else "research.domain.no_data"),
            )),
            RenderNodeV2(RenderNodeTypeV2.METRIC_ROW,"research.validation_funnel.recommendation.lost",children=(
                _leaf(RenderNodeTypeV2.METRIC_LABEL,"research.validation_funnel.recommendation.lost.label",key="research.validation_funnel.lost"),
                _leaf(RenderNodeTypeV2.METRIC_VALUE,"research.validation_funnel.recommendation.lost.value",value=s.validation_lost,fmt="INTEGER"),
            )),
            RenderNodeV2(RenderNodeTypeV2.METRIC_ROW,"research.validation_funnel.recommendation.solution",children=(
                _leaf(RenderNodeTypeV2.METRIC_LABEL,"research.validation_funnel.recommendation.solution.label",key="research.validation_funnel.solution"),
                _leaf(RenderNodeTypeV2.METRIC_VALUE,"research.validation_funnel.recommendation.solution.value",key=f"research.funnel.recommendation.{s.validation_recommendation.lower()}" if s.validation_funnel_available else "research.domain.no_data"),
            )),
        ))

def _strategy_degradation_table(items):
    columns=("strategy","symbol","oos","costs","stability","cycles","status","block")
    header=RenderNodeV2(RenderNodeTypeV2.TABLE_ROW,"research.degradation.header",children=tuple(
        _leaf(RenderNodeTypeV2.TABLE_HEADER_CELL,f"research.degradation.header.{code}",key=f"research.degradation.column.{code}") for code in columns))
    rows=[]
    for index,item in enumerate(items,start=1):
        block=("quarantine" if item.research_quarantine_required else
               "promotion" if item.promotion_blocked else "none")
        rows.append(RenderNodeV2(RenderNodeTypeV2.TABLE_ROW,f"research.degradation.{index}",
            state=RenderNodeStateV2(status_code="BLOCKED" if item.research_quarantine_required else "WARNING" if item.promotion_blocked else "OK"),children=(
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.degradation.{index}.strategy",value=item.strategy_code),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.degradation.{index}.symbol",value=item.symbol),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.degradation.{index}.oos",value=item.oos_retention_pct,fmt="DECIMAL"),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.degradation.{index}.costs",value=item.cost_retention_pct,fmt="DECIMAL"),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.degradation.{index}.stability",value=item.stability_retention_pct,fmt="DECIMAL"),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.degradation.{index}.cycles",value=item.consecutive_cycles,fmt="INTEGER"),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.degradation.{index}.status",key=f"research.degradation.status.{item.degradation_code.lower()}"),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.degradation.{index}.block",key=f"research.degradation.block.{block}"),
            )))
    return RenderNodeV2(RenderNodeTypeV2.TABLE,"research.degradation.table",children=(
        RenderNodeV2(RenderNodeTypeV2.TABLE_HEAD,"research.degradation.head",children=(header,)),
        RenderNodeV2(RenderNodeTypeV2.TABLE_BODY,"research.degradation.body",children=tuple(rows))))

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

def _methodology_failure_table(items):
    columns=("gate","failed","passed","not_evaluated","fail_pct","detail","status")
    header=RenderNodeV2(RenderNodeTypeV2.TABLE_ROW,"research.failures.header",children=tuple(
        _leaf(RenderNodeTypeV2.TABLE_HEADER_CELL,f"research.failures.header.{code}",key=f"research.failures.column.{code}") for code in columns))
    rows=[]
    for index,item in enumerate(items,start=1):
        status="WARNING" if item.status in ("NO_DATA","NOT_EVALUATED") else ("OK" if item.status == "PASS" else "BLOCKED")
        detail=(_leaf(RenderNodeTypeV2.TABLE_CELL,f"research.failures.{index}.detail",
                      key="research.failures.detail.base",
                      args={"costs":item.cost_failures,"sample":item.sample_failures})
                if item.gate_code == "base" else
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.failures.{index}.detail",
                      key="research.failures.detail.not_evaluated"
                          if item.not_evaluated == item.total else "research.failures.detail.evaluated",
                      args={"failed":item.failed,"passed":item.passed}))
        rows.append(RenderNodeV2(RenderNodeTypeV2.TABLE_ROW,f"research.failures.{index}",state=RenderNodeStateV2(status_code=status),children=(
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.failures.{index}.gate",key=f"research.failures.gate.{item.gate_code}"),
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.failures.{index}.failed",value=item.failed,fmt="INTEGER"),
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.failures.{index}.passed",value=item.passed,fmt="INTEGER"),
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.failures.{index}.not_evaluated",value=item.not_evaluated,fmt="INTEGER"),
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.failures.{index}.fail_pct",value=item.fail_pct,fmt="DECIMAL"),
            detail,
            _domain(RenderNodeTypeV2.TABLE_CELL,f"research.failures.{index}.status",item.status),
        ),action=RenderActionV2(
            "research.methodology.recheck",ActionKindV2.COMMAND,target_id=item.gate_code,
            command_code="RESEARCH.RUN_EDGE_SEARCH",policy_class="RESEARCH_MAINTENANCE",
            reversible=True,rollback_code="RESEARCH.CANCEL_PENDING_REQUEST",
            idempotency_key="client.request",
        )))
    return RenderNodeV2(RenderNodeTypeV2.TABLE,"research.failures.table",children=(
        RenderNodeV2(RenderNodeTypeV2.TABLE_HEAD,"research.failures.head",children=(header,)),
        RenderNodeV2(RenderNodeTypeV2.TABLE_BODY,"research.failures.body",children=tuple(rows))))

def _remediation_branch_table(items):
    columns=("branch","sources","created","pruned","queued","evaluated","gross","net","lost","pass","status","action")
    header=RenderNodeV2(RenderNodeTypeV2.TABLE_ROW,"research.remediation.header",children=tuple(
        _leaf(RenderNodeTypeV2.TABLE_HEADER_CELL,f"research.remediation.header.{code}",
              key=f"research.remediation.column.{code}") for code in columns))
    rows=[]
    for index,item in enumerate(items,start=1):
        state="OK" if item.oos_pass else "WARNING" if item.status != "FAILED" else "BLOCKED"
        rows.append(RenderNodeV2(RenderNodeTypeV2.TABLE_ROW,f"research.remediation.{index}",
            state=RenderNodeStateV2(status_code=state),children=(
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.remediation.{index}.branch",
                      key=f"research.remediation.branch.{item.branch_code.lower()}"),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.remediation.{index}.sources",value=item.source_failures,fmt="INTEGER"),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.remediation.{index}.created",value=item.created_variants,fmt="INTEGER"),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.remediation.{index}.pruned",value=item.pruned_variants,fmt="INTEGER"),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.remediation.{index}.queued",value=item.queued_variants,fmt="INTEGER"),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.remediation.{index}.evaluated",value=item.evaluated_variants,fmt="INTEGER"),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.remediation.{index}.gross",value=item.gross_pass,fmt="INTEGER"),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.remediation.{index}.net",value=item.after_costs_pass,fmt="INTEGER"),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.remediation.{index}.lost",value=item.cost_lost,fmt="INTEGER"),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.remediation.{index}.pass",value=item.oos_pass,fmt="INTEGER"),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.remediation.{index}.status",
                      key=_domain_key(item.status),args={"progress_pct":item.progress_pct,
                      "current_step":item.current_step,"updated_at":item.updated_at.isoformat() if item.updated_at else None}),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.remediation.{index}.action",
                      key="research.remediation.diagnostic" if item.diagnostic_only else "research.remediation.action",
                      args={"tooltip_key":"research.remediation.column.action"}),
            ),action=RenderActionV2(
                "research.request.refresh" if item.diagnostic_only else "research.edge_search.run",ActionKindV2.COMMAND,
                target_id=f"{item.process_id}|{item.branch_code}",
                command_code="RESEARCH.REQUEST_REFRESH" if item.diagnostic_only else "RESEARCH.RUN_EDGE_SEARCH",
                policy_class="RESEARCH_MAINTENANCE",reversible=True,
                rollback_code="RESEARCH.CANCEL_PENDING_REQUEST",idempotency_key="client.request",
            )))
    return RenderNodeV2(RenderNodeTypeV2.TABLE,"research.remediation.table",children=(
        RenderNodeV2(RenderNodeTypeV2.TABLE_HEAD,"research.remediation.head",children=(header,)),
        RenderNodeV2(RenderNodeTypeV2.TABLE_BODY,"research.remediation.body",children=tuple(rows))))

def _universe_table(items):
    columns=("selected","symbol","category","bars","rank","reason","status","operator_action")
    header=RenderNodeV2(RenderNodeTypeV2.TABLE_ROW,"research.universe.header",children=tuple(
        _leaf(RenderNodeTypeV2.TABLE_HEADER_CELL,f"research.universe.header.{code}",key=f"research.universe.column.{code}") for code in columns))
    rows=[]
    for index,item in enumerate(items,start=1):
        decision="SELECTED" if item.selected else "EXCLUDED"
        rows.append(RenderNodeV2(RenderNodeTypeV2.TABLE_ROW,f"research.universe.{index}",
            state=RenderNodeStateV2(status_code="OK" if item.selected else "WARNING"),children=(
                _domain(RenderNodeTypeV2.TABLE_CELL,f"research.universe.{index}.selected",decision),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.universe.{index}.symbol",value=item.symbol),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.universe.{index}.category",key=f"research.universe.category.{item.category_code.lower()}"),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.universe.{index}.bars",value=item.bars,fmt="INTEGER"),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.universe.{index}.rank",value=item.category_rank,fmt="INTEGER"),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.universe.{index}.reason",key=f"research.universe.reason.{item.reason_code.lower()}"),
                _process_status(f"research.universe.{index}.status",item),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.universe.{index}.operator_action",
                    key="research.operator_actions.open",args={"tooltip_key":"research.operator_actions.open.tooltip"}),
            ),action=RenderActionV2(
                "research.universe.include_next",ActionKindV2.COMMAND,target_id=item.symbol,
                command_code="RESEARCH.UNIVERSE_INCLUDE_NEXT",policy_class="RESEARCH_MAINTENANCE",
                reversible=True,rollback_code="RESEARCH.UNIVERSE_CLEAR_OVERRIDE",idempotency_key="client.request",
            )))
    return RenderNodeV2(RenderNodeTypeV2.TABLE,"research.universe.table",children=(
        RenderNodeV2(RenderNodeTypeV2.TABLE_HEAD,"research.universe.head",children=(header,)),
        RenderNodeV2(RenderNodeTypeV2.TABLE_BODY,"research.universe.body",children=tuple(rows))))

def _scout_table(items):
    columns=("decision","symbol","category","score","capacity","correlation","bars","reason","action","status","operator_action")
    header=RenderNodeV2(RenderNodeTypeV2.TABLE_ROW,"research.scout.header",children=tuple(
        _leaf(RenderNodeTypeV2.TABLE_HEADER_CELL,f"research.scout.header.{code}",key=f"research.scout.column.{code}") for code in columns))
    reasons={"CATEGORY_QUOTA_SELECTED":"Квота категории","CATEGORY_QUOTA_EXCEEDED":"Резерв категории",
             "NEXT_FUTURES_CONTRACT":"Следующий контракт","INSUFFICIENT_OR_STALE_BARS":"Нужна история",
             "SPECIFICATION_NOT_READY":"Нет спецификации",
             "VOLATILITY_OBSERVATION_ONLY":"Пока только наблюдение: волатильность или исполнимость ниже допуска",
             "LIQUIDITY_NOT_READY":"Недостаточная ликвидность"}
    actions={"RESEARCH_NEXT":"Исследовать","KEEP_RESERVE":"Оставить в резерве",
             "WAIT_ROLL":"Ждать роллирования","COLLECT_DATA":"Собирать данные","VERIFY_SPEC":"Проверить контракт",
             "KEEP_OBSERVING":"Продолжать наблюдение","COLLECT_LIQUIDITY":"Накопить ликвидность"}
    rows=[]
    for index,item in enumerate(items,start=1):
        status="OK" if item.decision_code=="SELECTED" else "WARNING" if item.decision_code in ("BACKFILL","RESERVE") else "BLOCKED"
        rows.append(RenderNodeV2(RenderNodeTypeV2.TABLE_ROW,f"research.scout.{item.decision_code.lower()}.{index}",state=RenderNodeStateV2(status_code=status),children=(
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.scout.{index}.decision",key=f"research.scout.decision.{item.decision_code.lower()}"),
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.scout.{index}.symbol",value=item.symbol),
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.scout.{index}.category",key=f"research.universe.category.{item.category_code.lower()}"),
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.scout.{index}.score",value=item.research_score,fmt="DECIMAL"),
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.scout.{index}.capacity",value=item.capacity_rub,fmt="DECIMAL"),
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.scout.{index}.correlation",value=item.max_abs_correlation,fmt="DECIMAL"),
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.scout.{index}.bars",value=item.bars,fmt="INTEGER"),
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.scout.{index}.reason",value=reasons.get(item.reason_code,item.reason_code)),
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.scout.{index}.action",value=actions.get(item.next_action_code,item.next_action_code)),
            _process_status(f"research.scout.{index}.status",item),
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.scout.{index}.operator_action",
                key="research.operator_actions.open",args={"tooltip_key":"research.operator_actions.open.tooltip"}),
        ),action=RenderActionV2("research.universe.include_next",ActionKindV2.COMMAND,target_id=item.symbol,
            command_code="RESEARCH.UNIVERSE_INCLUDE_NEXT",policy_class="RESEARCH_MAINTENANCE",
            reversible=True,rollback_code="RESEARCH.UNIVERSE_CLEAR_OVERRIDE",idempotency_key="client.request")))
    return RenderNodeV2(RenderNodeTypeV2.TABLE,"research.scout.table",children=(
        RenderNodeV2(RenderNodeTypeV2.TABLE_HEAD,"research.scout.head",children=(header,)),
        RenderNodeV2(RenderNodeTypeV2.TABLE_BODY,"research.scout.body",children=tuple(rows))))

def _instrument_funnel(s):
    stages=(("discovered",s.scout_discovered),("data_spec",s.scout_specification_pass),
            ("liquidity",s.scout_liquidity_pass),("volatility",s.scout_information_ranked),
            ("quota",s.scout_selected),("coarse",s.scout_coarse_queued))
    return RenderNodeV2(RenderNodeTypeV2.GRID,"research.scout.funnel",children=tuple(
        RenderNodeV2(RenderNodeTypeV2.CARD,f"research.scout.funnel.{code}",
          state=RenderNodeStateV2(status_code="OK" if value else "WARNING"),children=(
            _leaf(RenderNodeTypeV2.TITLE,f"research.scout.funnel.{code}.title",key=f"research.scout.funnel.{code}"),
            _leaf(RenderNodeTypeV2.METRIC_VALUE,f"research.scout.funnel.{code}.value",value=value,fmt="INTEGER"),
        )) for code,value in stages))

def _scout_schedule(s):
    return RenderNodeV2(RenderNodeTypeV2.CARD,"research.scout.schedule",state=RenderNodeStateV2(
        status_code="BLOCKED" if s.scout_scheduler_status in ("FAILED","TIMEOUT") else "OK"),children=(
        _leaf(RenderNodeTypeV2.TITLE,"research.scout.schedule.title",key="research.scout.schedule.title"),
        _metric("scout_last_run",s.scout_last_run_at,"DATETIME"),
        _metric("scout_next_run",s.scout_next_run_at,"DATETIME"),
        _leaf(RenderNodeTypeV2.METRIC_VALUE,"research.scout.schedule.status",
            key=f"research.domain.{s.scout_scheduler_status.lower()}"),
    ))

def _futures_roll_table(items):
    columns=("status","root","current","next","selected","expiry","liquidity","decision","leverage","limit")
    header=RenderNodeV2(RenderNodeTypeV2.TABLE_ROW,"research.futures.header",children=tuple(
        _leaf(RenderNodeTypeV2.TABLE_HEADER_CELL,f"research.futures.header.{code}",key=f"research.futures.column.{code}") for code in columns))
    rows=[]
    for index,item in enumerate(items,start=1):
        status="OK" if item.status_code=="READY" else "WARNING"
        status_key=f"research.futures.status.{item.status_code.lower()}"
        rows.append(RenderNodeV2(RenderNodeTypeV2.TABLE_ROW,f"research.futures.{index}",
            state=RenderNodeStateV2(status_code=status),children=(
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.futures.{index}.status",key=status_key,
                    args={"tooltip_key":f"{status_key}.tooltip","progress_pct":item.progress_pct}),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.futures.{index}.root",value=item.root_symbol),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.futures.{index}.current",value=item.current_symbol),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.futures.{index}.next",value=item.next_symbol),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.futures.{index}.selected",value=item.selected_symbol),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.futures.{index}.expiry",value=item.days_to_expiry,fmt="INTEGER"),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.futures.{index}.liquidity",key="research.futures.liquidity",
                    args={"current":round(item.current_volume,1),"next":round(item.next_volume,1),"progress_pct":item.progress_pct}),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.futures.{index}.decision",key=f"research.futures.decision.{item.decision_code.lower()}"),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.futures.{index}.leverage",key="research.futures.leverage_value",
                    args={"value":item.max_leverage,"margin_source":item.margin_source}),
                _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.futures.{index}.limit",key="research.futures.percent",
                    args={"value":item.max_position_pct}),
            )))
    return RenderNodeV2(RenderNodeTypeV2.TABLE,"research.futures.table",children=(
        RenderNodeV2(RenderNodeTypeV2.TABLE_HEAD,"research.futures.head",children=(header,)),
        RenderNodeV2(RenderNodeTypeV2.TABLE_BODY,"research.futures.body",children=tuple(rows))))

def _futures_card_metric(index,code,*,value=None,key=None,args=None,fmt=None):
    return RenderNodeV2(RenderNodeTypeV2.METRIC_ROW,f"research.futures.{index}.{code}",children=(
        _leaf(RenderNodeTypeV2.METRIC_LABEL,f"research.futures.{index}.{code}.label",key=f"research.futures.card.{code}"),
        _leaf(RenderNodeTypeV2.METRIC_VALUE,f"research.futures.{index}.{code}.value",value=value,key=key,args=args,fmt=fmt),
    ))

def _futures_roll_cards(items):
    cards=[]
    for index,item in enumerate(items,start=1):
        status_key=f"research.futures.status.{item.status_code.lower()}"
        cards.append(RenderNodeV2(RenderNodeTypeV2.CARD,f"research.futures.card.{item.root_symbol.lower()}",
            state=RenderNodeStateV2(status_code="OK" if item.status_code=="READY" else "WARNING"),children=(
                _leaf(RenderNodeTypeV2.TITLE,f"research.futures.{index}.title",value=item.root_symbol),
                _leaf(RenderNodeTypeV2.METRIC_VALUE,f"research.futures.{index}.status",key=status_key,
                    args={"progress_pct":item.progress_pct}),
                _futures_card_metric(index,"working",value=item.selected_symbol),
                _futures_card_metric(index,"next",value=item.next_symbol),
                _futures_card_metric(index,"expiry",value=item.days_to_expiry,fmt="INTEGER"),
                _futures_card_metric(index,"liquidity",key="research.futures.liquidity",
                    args={"current":round(item.current_volume,1),"next":round(item.next_volume,1),"progress_pct":item.progress_pct}),
                _futures_card_metric(index,"decision",key=f"research.futures.decision.{item.decision_code.lower()}"),
                _futures_card_metric(index,"leverage",key="research.futures.leverage_value",
                    args={"value":item.max_leverage,"margin_source":item.margin_source}),
                _futures_card_metric(index,"limit",key="research.futures.percent",args={"value":item.max_position_pct}),
            )))
    return RenderNodeV2(RenderNodeTypeV2.GRID,"research.futures.cards",children=tuple(cards))

def _run_audit_table(items):
    columns=("status","started","steps","duration","outcome","reason","analysis","recommendation")
    header=RenderNodeV2(RenderNodeTypeV2.TABLE_ROW,"research.audit.header",children=tuple(_leaf(RenderNodeTypeV2.TABLE_HEADER_CELL,f"research.audit.header.{code}",key=f"research.audit.column.{code}") for code in columns))
    rows=[]
    for index,item in enumerate(items,start=1):
        rows.append(RenderNodeV2(RenderNodeTypeV2.TABLE_ROW,f"research.audit.{index}",children=(
            _process_status(f"research.audit.{index}.status",item),
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.audit.{index}.started",value=item.started_at,fmt="DATETIME"),
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.audit.{index}.steps",key="research.audit.steps",args={"completed":item.steps_completed,"total":item.steps_total}),
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.audit.{index}.duration",value=item.duration_seconds,fmt="INTEGER"),
            _domain(RenderNodeTypeV2.TABLE_CELL,f"research.audit.{index}.outcome",item.outcome),
            _domain(RenderNodeTypeV2.TABLE_CELL,f"research.audit.{index}.reason",item.reason),
            _leaf(RenderNodeTypeV2.TABLE_CELL,f"research.audit.{index}.analysis",value=item.explanation),
            _recommendation(f"research.audit.{index}.recommendation",item),
        ),action=RenderActionV2(
            "research.edge_search.run",ActionKindV2.COMMAND,
            target_id=item.process_id,command_code="RESEARCH.RUN_EDGE_SEARCH",policy_class="RESEARCH_MAINTENANCE",
            reversible=True,rollback_code="RESEARCH.CANCEL_PENDING_REQUEST",
            idempotency_key="client.request",
        )))
    return RenderNodeV2(RenderNodeTypeV2.TABLE,"research.audit.table",children=(RenderNodeV2(RenderNodeTypeV2.TABLE_HEAD,"research.audit.head",children=(header,)),RenderNodeV2(RenderNodeTypeV2.TABLE_BODY,"research.audit.body",children=tuple(rows))))

def _current_cycle_card(s):
    item=s.edge_search_runs[0] if s.edge_search_runs else None
    if item is None:
        return RenderNodeV2(RenderNodeTypeV2.CARD,"research.current",state=RenderNodeStateV2(status_code="WARNING"),children=(
            _leaf(RenderNodeTypeV2.TITLE,"research.current.title",key="research.current.title"),
            _leaf(RenderNodeTypeV2.METRIC_VALUE,"research.current.empty",key="research.domain.no_data"),
        ))
    status="BLOCKED" if item.status == "FAILED" else "OK" if item.status == "SUCCEEDED" else "WARNING"
    running=item.status in {"PENDING","QUEUED","RUNNING"}
    rows=[
        _leaf(RenderNodeTypeV2.TITLE,"research.current.title",key="research.current.title"),
        RenderNodeV2(RenderNodeTypeV2.METRIC_ROW,"research.current.status",children=(
            _leaf(RenderNodeTypeV2.METRIC_LABEL,"research.current.status.label",key="research.current.status"),
            _domain(RenderNodeTypeV2.METRIC_VALUE,"research.current.status.value",item.status),
        )),
        RenderNodeV2(RenderNodeTypeV2.METRIC_ROW,"research.current.stage",children=(
            _leaf(RenderNodeTypeV2.METRIC_LABEL,"research.current.stage.label",key="research.current.stage"),
            _domain(RenderNodeTypeV2.METRIC_VALUE,"research.current.stage.value",item.current_step),
        )),
        RenderNodeV2(RenderNodeTypeV2.METRIC_ROW,"research.current.progress",children=(
            _leaf(RenderNodeTypeV2.METRIC_LABEL,"research.current.progress.label",key="research.current.progress"),
            _leaf(RenderNodeTypeV2.METRIC_VALUE,"research.current.progress.value",value=item.progress_pct,fmt="DECIMAL"),
        )),
        RenderNodeV2(RenderNodeTypeV2.METRIC_ROW,"research.current.reason",children=(
            _leaf(RenderNodeTypeV2.METRIC_LABEL,"research.current.reason.label",key="research.current.reason"),
            _leaf(RenderNodeTypeV2.METRIC_VALUE,"research.current.reason.value",key="research.current.running") if running else _domain(RenderNodeTypeV2.METRIC_VALUE,"research.current.reason.value",item.reason),
        )),
        RenderNodeV2(RenderNodeTypeV2.METRIC_ROW,"research.current.next",children=(
            _leaf(RenderNodeTypeV2.METRIC_LABEL,"research.current.next.label",key="research.current.next"),
            _leaf(RenderNodeTypeV2.METRIC_VALUE,"research.current.next.value",key="research.current.wait") if running else _domain(RenderNodeTypeV2.METRIC_VALUE,"research.current.next.value",item.recommendation),
        )),
    ]
    if s.regime_tasks_total:
        rows.extend((
            RenderNodeV2(RenderNodeTypeV2.METRIC_ROW,"research.current.regime_tasks",children=(
                _leaf(RenderNodeTypeV2.METRIC_LABEL,"research.current.regime_tasks.label",key="research.current.regime_tasks"),
                _leaf(RenderNodeTypeV2.METRIC_VALUE,"research.current.regime_tasks.value",key="research.current.regime_tasks.value",args={"completed":s.regime_tasks_completed,"total":s.regime_tasks_total}),
            )),
            RenderNodeV2(RenderNodeTypeV2.METRIC_ROW,"research.current.regime_progress",children=(
                _leaf(RenderNodeTypeV2.METRIC_LABEL,"research.current.regime_progress.label",key="research.current.regime_progress"),
                _leaf(RenderNodeTypeV2.METRIC_VALUE,"research.current.regime_progress.value",value=s.regime_progress_pct,fmt="DECIMAL"),
            )),
        ))
    return RenderNodeV2(RenderNodeTypeV2.CARD,"research.current",state=RenderNodeStateV2(status_code=status),children=tuple(rows))

def _operating_cycle_card(s):
    status="OK" if s.live_chain_status == "HEALTHY" else "WARNING" if s.live_chain_status in {"WAITING","ATTENTION"} else "BLOCKED"
    return RenderNodeV2(RenderNodeTypeV2.CARD,"research.operating",
        state=RenderNodeStateV2(status_code=status),children=(
            _leaf(RenderNodeTypeV2.TITLE,"research.operating.title",key="research.operating.title"),
            RenderNodeV2(RenderNodeTypeV2.METRIC_ROW,"research.operating.phase",children=(
                _leaf(RenderNodeTypeV2.METRIC_LABEL,"research.operating.phase.label",key="research.operating.phase"),
                _domain(RenderNodeTypeV2.METRIC_VALUE,"research.operating.phase.value",s.operating_phase),
            )),
            RenderNodeV2(RenderNodeTypeV2.METRIC_ROW,"research.operating.status",children=(
                _leaf(RenderNodeTypeV2.METRIC_LABEL,"research.operating.status.label",key="research.operating.status"),
                _domain(RenderNodeTypeV2.METRIC_VALUE,"research.operating.status.value",s.live_chain_status),
            )),
            RenderNodeV2(RenderNodeTypeV2.METRIC_ROW,"research.operating.next",children=(
                _leaf(RenderNodeTypeV2.METRIC_LABEL,"research.operating.next.label",key="research.operating.next"),
                _leaf(RenderNodeTypeV2.METRIC_VALUE,"research.operating.next.value",value=s.next_session_at,
                    fmt="DATETIME",key=None if s.next_session_at else "research.operating.session_open"),
            )),
            RenderNodeV2(RenderNodeTypeV2.METRIC_ROW,"research.operating.audit",children=(
                _leaf(RenderNodeTypeV2.METRIC_LABEL,"research.operating.audit.label",key="research.operating.audit"),
                _domain(RenderNodeTypeV2.METRIC_VALUE,"research.operating.audit.value",s.historical_audit_status),
            )),
        ))


def _ngu6_oos_metric(
    code,
    label,
    *,
    value=None,
    fmt=None,
):
    return RenderNodeV2(
        RenderNodeTypeV2.METRIC_ROW,
        f"research.ngu6_oos.{code}",
        children=(
            _leaf(
                RenderNodeTypeV2.METRIC_LABEL,
                f"research.ngu6_oos.{code}.label",
                value=label,
            ),
            _leaf(
                RenderNodeTypeV2.METRIC_VALUE,
                f"research.ngu6_oos.{code}.value",
                value=value,
                fmt=fmt,
            ),
        ),
    )


def _ngu6_oos_panel():
    s = resolve_ngu6_frozen_day_oos_status_v1()

    monitor_ok = (
        s.health_code == "HEALTHY"
        and s.timer_active == "active"
        and s.timer_substate == "waiting"
        and s.service_result == "success"
        and s.service_exec_status == "0"
    )

    dataset_ok = (
        s.dataset_freshness == "CURRENT"
    )

    oos_event = (
        s.new_completed_day_trades > 0
    )

    health_state = (
        "OK"
        if monitor_ok
        else "WARNING"
    )

    dataset_state = (
        "OK"
        if dataset_ok
        else "WARNING"
    )

    oos_state = (
        "WARNING"
        if oos_event
        else "OK"
    )

    headline_text = " · ".join(
        (
            (
                "HEALTHY"
                if monitor_ok
                else "ATTENTION"
            ),
            (
                "TIMER WAITING"
                if (
                    s.timer_active == "active"
                    and s.timer_substate == "waiting"
                )
                else "TIMER ATTENTION"
            ),
            (
                "DATA CURRENT"
                if dataset_ok
                else f"DATA {s.dataset_freshness}"
            ),
            (
                "NEW OOS TRADE"
                if oos_event
                else "NO NEW TRADE"
            ),
        )
    )

    status_bar = RenderNodeV2(
        RenderNodeTypeV2.CARD,
        "research.ngu6_oos.status_bar",
        state=RenderNodeStateV2(
            status_code=(
                "WARNING"
                if (
                    not monitor_ok
                    or not dataset_ok
                    or oos_event
                )
                else "OK"
            )
        ),
        children=(
            _leaf(
                RenderNodeTypeV2.TITLE,
                "research.ngu6_oos.status_bar.title",
                value="NGU6 Frozen DAY OOS",
            ),
            _leaf(
                RenderNodeTypeV2.BADGE,
                "research.ngu6_oos.status_bar.badge",
                value=(
                    "HEALTHY"
                    if (
                        monitor_ok
                        and dataset_ok
                        and not oos_event
                    )
                    else "ATTENTION"
                ),
            ),
            _leaf(
                RenderNodeTypeV2.TEXT,
                "research.ngu6_oos.status_bar.summary",
                value=headline_text,
            ),
            _leaf(
                RenderNodeTypeV2.TEXT,
                "research.ngu6_oos.status_bar.readonly",
                value=(
                    "READ-ONLY · параметрический поиск запрещён · "
                    "PnL не раскрывается"
                ),
            ),
        ),
    )

    monitor_card = RenderNodeV2(
        RenderNodeTypeV2.CARD,
        "research.ngu6_oos.monitor",
        state=RenderNodeStateV2(
            status_code=health_state
        ),
        children=(
            _leaf(
                RenderNodeTypeV2.TITLE,
                "research.ngu6_oos.monitor.title",
                value="Monitor",
            ),
            _ngu6_oos_metric(
                "timer",
                "Timer",
                value=(
                    f"{s.timer_active} / "
                    f"{s.timer_substate}"
                ),
            ),
            _ngu6_oos_metric(
                "last_run",
                "Последний запуск",
                value=s.last_trigger,
            ),
            _ngu6_oos_metric(
                "next_run",
                "Следующий запуск",
                value=s.next_trigger,
            ),
            _ngu6_oos_metric(
                "service",
                "Service",
                value=(
                    f"{s.service_result} / "
                    f"{s.service_exec_status}"
                ),
            ),
        ),
    )

    dataset_card = RenderNodeV2(
        RenderNodeTypeV2.CARD,
        "research.ngu6_oos.dataset",
        state=RenderNodeStateV2(
            status_code=dataset_state
        ),
        children=(
            _leaf(
                RenderNodeTypeV2.TITLE,
                "research.ngu6_oos.dataset.title",
                value="NATIVE_FINAM_M5_V1",
            ),
            _ngu6_oos_metric(
                "dataset_rows",
                "Строк",
                value=s.dataset_rows,
                fmt="INTEGER",
            ),
            _ngu6_oos_metric(
                "dataset_last",
                "Последний M5",
                value=(
                    s.dataset_last
                    if s.dataset_last is not None
                    else "UNAVAILABLE"
                ),
                fmt=(
                    "DATETIME"
                    if s.dataset_last is not None
                    else None
                ),
            ),
            _ngu6_oos_metric(
                "dataset_freshness",
                "Актуальность",
                value=s.dataset_freshness,
            ),
            _ngu6_oos_metric(
                "dataset_age",
                "Возраст, сек.",
                value=(
                    s.dataset_age_seconds
                    if s.dataset_age_seconds is not None
                    else "UNAVAILABLE"
                ),
                fmt=(
                    "INTEGER"
                    if s.dataset_age_seconds is not None
                    else None
                ),
            ),
        ),
    )

    oos_card = RenderNodeV2(
        RenderNodeTypeV2.CARD,
        "research.ngu6_oos.oos3",
        state=RenderNodeStateV2(
            status_code=oos_state
        ),
        children=(
            _leaf(
                RenderNodeTypeV2.TITLE,
                "research.ngu6_oos.oos3.title",
                value="Frozen OOS3",
            ),
            _ngu6_oos_metric(
                "boundary",
                "Boundary",
                value=s.oos3_boundary,
            ),
            _ngu6_oos_metric(
                "new_trades",
                "Новых DAY-сделок",
                value=s.new_completed_day_trades,
                fmt="INTEGER",
            ),
            _ngu6_oos_metric(
                "inventory",
                "Inventory",
                value=(
                    "FROZEN"
                    if s.inventory_frozen
                    else "WAITING"
                ),
            ),
            _ngu6_oos_metric(
                "pnl",
                "PnL",
                value=(
                    "REVEALED"
                    if s.pnl_revealed
                    else "HIDDEN"
                ),
            ),
            _ngu6_oos_metric(
                "verdict",
                "Verdict",
                value=s.last_verdict,
            ),
        ),
    )

    panel_children = [
        status_bar,
        RenderNodeV2(
            RenderNodeTypeV2.GRID,
            "research.ngu6_oos.cards",
            children=(
                monitor_card,
                dataset_card,
                oos_card,
            ),
        ),
    ]

    panel_children.extend(
        (
            _leaf(
                RenderNodeTypeV2.TITLE,
                "research.ngu6_oos.events.title",
                value="Значимые OOS-события",
                level="SECTION",
            ),
        )
    )

    if not s.events:
        panel_children.append(
            _leaf(
                RenderNodeTypeV2.TEXT,
                "research.ngu6_oos.events.empty",
                value="Значимых OOS-событий пока нет.",
            )
        )
        return tuple(panel_children)

    event_rows = []

    for index, event in enumerate(
        s.events,
        start=1,
    ):
        event_rows.append(
            RenderNodeV2(
                RenderNodeTypeV2.TABLE_ROW,
                f"research.ngu6_oos.event.{index}",
                state=RenderNodeStateV2(
                    status_code=(
                        "WARNING"
                        if event.event_type
                        in {
                            "FAIL_CLOSED",
                            "NEW_INVENTORY",
                        }
                        else "OK"
                    )
                ),
                children=(
                    _leaf(
                        RenderNodeTypeV2.TABLE_CELL,
                        f"research.ngu6_oos."
                        f"event.{index}.type",
                        value=event.event_type,
                    ),
                    _leaf(
                        RenderNodeTypeV2.TABLE_CELL,
                        f"research.ngu6_oos."
                        f"event.{index}.text",
                        value=event.text,
                    ),
                ),
            )
        )

    events_table = RenderNodeV2(
        RenderNodeTypeV2.TABLE,
        "research.ngu6_oos.events",
        children=(
            RenderNodeV2(
                RenderNodeTypeV2.TABLE_HEAD,
                "research.ngu6_oos.events.head",
                children=(
                    RenderNodeV2(
                        RenderNodeTypeV2.TABLE_ROW,
                        "research.ngu6_oos.events.header",
                        children=(
                            _leaf(
                                RenderNodeTypeV2.TABLE_HEADER_CELL,
                                "research.ngu6_oos.events."
                                "header.type",
                                value="Событие",
                            ),
                            _leaf(
                                RenderNodeTypeV2.TABLE_HEADER_CELL,
                                "research.ngu6_oos.events."
                                "header.text",
                                value="Детали",
                            ),
                        ),
                    ),
                ),
            ),
            RenderNodeV2(
                RenderNodeTypeV2.TABLE_BODY,
                "research.ngu6_oos.events.body",
                children=tuple(event_rows),
            ),
        ),
    )

    panel_children.append(events_table)

    return tuple(panel_children)

def render_research_domain_v2(s: ResearchSnapshotV2, *, timezone_code="Europe/Moscow"):
    times=[x for x in (s.last_cycle_at,s.summary_refreshed_at,s.queue_updated_at,s.oos_updated_at) if x]
    source_as_of=min(times) if times else s.generated_at
    tiles=(
        _tile("instruments",s.active_symbols,"OK" if s.active_symbols else "WARNING",
              "research.tile.status.ready" if s.active_symbols else "research.tile.status.empty"),
        _tile("live_signals",s.live_signals_1h,"OK" if s.live_signals_1h else "WARNING",
              "research.tile.status.found" if s.live_signals_1h else "research.tile.status.empty"),
        _tile("paper_fills",s.paper_fills_1h,"OK" if s.paper_fills_1h else "WARNING",
              "research.tile.status.found" if s.paper_fills_1h else "research.tile.status.empty"),
        _tile("closed_trades",s.closed_trades_1h,"OK" if s.closed_trades_1h else "WARNING",
              "research.tile.status.found" if s.closed_trades_1h else "research.tile.status.empty"),
        _tile("candidates",s.candidates,"OK" if s.candidates else "WARNING",
              "research.tile.status.found" if s.candidates else "research.tile.status.empty"),
        _tile("regime_progress",s.regime_progress_pct,
              "OK" if s.regime_status == "COMPLETE" else "WARNING",
              "research.tile.status.ready" if s.regime_status == "COMPLETE" else "research.tile.status.running"),
        _tile("oos_pass",s.oos_pass_total,"OK" if s.oos_pass_total else "WARNING",
              "research.tile.status.pass" if s.oos_pass_total else "research.tile.status.no_pass"),
        _tile("queue",s.queue_pending,"WARNING" if s.queue_pending else "OK",
              "research.tile.status.queue" if s.queue_pending else "research.tile.status.empty"),
    )
    governance_tiles=(
        _tile("global_trials",s.global_trials,"OK" if s.global_trials else "WARNING"),
        _tile("global_pass",s.global_significance_pass,"OK" if s.global_significance_pass else "WARNING"),
        _tile("holdout",s.holdout_opened,"BLOCKED" if s.holdout_reuse_blocked else ("OK" if s.holdout_opened else "WARNING")),
        _tile("pnl_units",s.pnl_units_ready,"BLOCKED" if s.pnl_units_blocked else ("OK" if s.pnl_units_ready else "WARNING")),
        _tile("equities",s.equity_experiments,"OK" if s.equity_experiments else "WARNING"),
        _tile("futures",s.futures_experiments,"OK" if s.futures_experiments else "WARNING"),
        _tile("portfolio",s.portfolio_selected,"OK" if s.portfolio_selected else "WARNING"),
    )
    refresh=RenderNodeV2(RenderNodeTypeV2.ACTION,"research.action.refresh",content=RenderContentV2(message_key="research.action.request_refresh"),action=RenderActionV2("research.request.refresh",ActionKindV2.COMMAND,command_code="RESEARCH.REQUEST_REFRESH",policy_class="RESEARCH_MAINTENANCE",reversible=True,rollback_code="RESEARCH.CANCEL_PENDING_REQUEST",idempotency_key="client.request"))
    edge_search=RenderNodeV2(RenderNodeTypeV2.ACTION,"research.action.edge_search",content=RenderContentV2(message_key="research.action.run_edge_search"),action=RenderActionV2("research.edge_search.run",ActionKindV2.COMMAND,command_code="RESEARCH.RUN_EDGE_SEARCH",policy_class="RESEARCH_MAINTENANCE",reversible=True,rollback_code="RESEARCH.CANCEL_PENDING_REQUEST",idempotency_key="client.request"))
    children=[
        _leaf(RenderNodeTypeV2.TITLE,"research.title",key="research.workspace.title",level="PAGE"),
        _leaf(RenderNodeTypeV2.SUBTITLE,"research.subtitle",key="research.workspace.subtitle"),
        RenderNodeV2(RenderNodeTypeV2.GRID,"research.tiles",children=tiles),
        _operating_cycle_card(s),
        _current_cycle_card(s),
    ]
    children.extend(_ngu6_oos_panel())
    if s.remediation_branches:
        children.extend((_leaf(RenderNodeTypeV2.TITLE,"research.remediation.title",
                               key="research.remediation.title",level="SECTION"),
                         _remediation_branch_table(s.remediation_branches)))
    if s.validation_funnel_available:
        children.extend((_leaf(RenderNodeTypeV2.TITLE,"research.validation_funnel.title",key="research.validation_funnel.title",level="SECTION"),_validation_funnel_tiles(s),_validation_funnel_recommendation(s)))
    if s.strategy_degradation:
        children.extend((_leaf(RenderNodeTypeV2.TITLE,"research.degradation.title",key="research.degradation.title",level="SECTION"),_strategy_degradation_table(s.strategy_degradation)))
    if s.global_trials:
        children.extend((_leaf(RenderNodeTypeV2.TITLE,"research.governance.title",key="research.governance.title",level="SECTION"),RenderNodeV2(RenderNodeTypeV2.GRID,"research.governance.tiles",children=governance_tiles)))
    children.extend((_leaf(RenderNodeTypeV2.TITLE,"research.futures.title",key="research.futures.title",level="SECTION"),_futures_roll_cards(s.futures_roll_items),_leaf(RenderNodeTypeV2.TITLE,"research.scout.title",key="research.scout.title",level="SECTION"),_scout_schedule(s),_leaf(RenderNodeTypeV2.TITLE,"research.scout.funnel.title",key="research.scout.funnel.title",level="SECTION"),_instrument_funnel(s),_scout_table(s.scout_items),_leaf(RenderNodeTypeV2.TITLE,"research.universe.title",key="research.universe.title",level="SECTION"),_universe_table(s.universe_items),_leaf(RenderNodeTypeV2.TITLE,"research.failures.title",key="research.failures.title",level="SECTION"),_methodology_failure_table(s.methodology_failures),_leaf(RenderNodeTypeV2.TITLE,"research.audit.title",key="research.audit.title",level="SECTION"),_run_audit_table(s.edge_search_runs),_leaf(RenderNodeTypeV2.TITLE,"research.algorithms.title",key="research.algorithms.title",level="SECTION"),_algorithm_table(s.algorithm_results)))
    d=RenderDocumentV2(document_id="operator.research.v2",locale_code="ru-RU",fallback_locale_code="ru-RU",timezone_code=timezone_code,generated_at=s.generated_at,source_as_of=source_as_of,quality_code="MIXED_FRESHNESS",root=RenderNodeV2(RenderNodeTypeV2.WORKSPACE,"workspace.research",children=(RenderNodeV2(RenderNodeTypeV2.PAGE,"page.research",state=RenderNodeStateV2(status_code="WARNING",quality_code="MIXED_FRESHNESS"),children=tuple(children)),)))
    validate_render_document_v2(d); return d
