from __future__ import annotations

import json

from marketcore.presentation.render_tree.node_types import RenderNodeType
from marketcore.presentation.render_tree.render_document import RenderDocument
from marketcore.presentation.render_tree.render_node import RenderNode
from marketcore.presentation.framework.i18n_resolver import UiI18nResolverV1
from marketcore.presentation.framework.theme_model import ThemeModel
from marketcore.presentation.framework.theme_resolver import ThemeResolverV1
from marketcore.presentation.components.data_table_node import (
    DataTableColumn,
    data_table_node,
)
from marketcore.presentation.workspace_v2.viewmodel.control_center_v2_viewmodel import (
    ControlCenterV2ViewModel,
    RelationshipCandidateV2,
)


def _title(text: str, level: int) -> RenderNode:
    return RenderNode(RenderNodeType.TITLE, props={"level": level}, text=text)


def _metric(label: str, value: str) -> RenderNode:
    return RenderNode(
        RenderNodeType.METRIC_ROW,
        props={"class": "mc-v2-value-row"},
        children=(
            RenderNode(RenderNodeType.METRIC_LABEL, text=label),
            RenderNode(RenderNodeType.METRIC_VALUE, props={"class": "mc-v2-metric-value"}, text=value),
        ),
    )


def _resource_code(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def _parameter_text(parameters: dict, i18n: UiI18nResolverV1) -> str:
    return " · ".join(
        f"{i18n.text(f'research.parameter.{_resource_code(str(key))}')} {value}"
        for key, value in sorted(parameters.items())
    )


def _quality_reason_text(row: dict, i18n: UiI18nResolverV1) -> str:
    codes = row.get("reason_codes") or []
    return " · ".join(i18n.text(f"quality.reason.{_resource_code(str(code))}") for code in codes) or "—"


def _theme_px(theme: ThemeModel, property_code: str) -> str:
    value = theme.get(property_code)
    if not value:
        raise RuntimeError(f"THEME_PROPERTY_NOT_FOUND:{property_code}")
    return f"{int(value)}px"


def _recommendation_options(vm: ControlCenterV2ViewModel, code: str, i18n: UiI18nResolverV1) -> str:
    if code == "VOLATILITY":
        values = [{"value": str(row.get("regime_group") or "unknown"), "label": str(row.get("regime_group") or "unknown"), "enabled": int(row.get("passed") or 0) > 0} for row in vm.volatility_analysis]
    elif code == "SETUP":
        values = [{"value": str(row.get("policy_code") or row.get("strategy_code") or "observe"), "label": _parameter_text(row.get("parameter_json") or {}, i18n), "enabled": bool(row.get("promotion_allowed"))} for row in vm.entry_analysis]
    elif code == "EXECUTION":
        values = [{"value": str(row.get("mode") or "observe"), "label": f"{row.get('mode')}: {int(row.get('fills') or 0)}", "enabled": bool(row.get("quotes_verified"))} for row in vm.execution_quality]
    elif code == "RISK":
        values = [{"value": str(row.get("symbol") or "observe"), "label": f"{row.get('symbol')}: {row.get('risk_decision_code')}", "enabled": bool(row.get("ready_for_paper"))} for row in vm.risk_analysis]
    else:
        values = [{"value": "observe", "label": i18n.text("research.solution.collect_evidence"), "enabled": True}]
    if not any(bool(item.get("enabled")) for item in values):
        for row in vm.shadow_requirements:
            values.append({"value": f"observe-{row.get('timeframe')}", "label": f"{row.get('timeframe')}: закрыто {int(row.get('closed') or 0)} из {int(row.get('minimum_closed') or 0)} — не хватает {int(row.get('missing_closed') or 0)}; сессий {int(row.get('sessions') or 0)} из {int(row.get('minimum_sessions') or 0)} — не хватает {int(row.get('missing_sessions') or 0)}", "enabled": True})
        if len(values) == 0:
            values.append({"value": "observe", "label": i18n.text("research.solution.collect_evidence"), "enabled": True})
    return json.dumps(values, ensure_ascii=False)


def _relationship_card(item: RelationshipCandidateV2, i18n: UiI18nResolverV1) -> RenderNode:
    return RenderNode(
        RenderNodeType.CARD,
        props={"class": "mc-v2-card", "style": "grid-column:auto;min-height:0", "data-card": "KPI", "data-status": item.status},
        children=(
            _title(item.family, 3),
            RenderNode(RenderNodeType.TEXT, text=f"{item.source} → {item.target}"),
            RenderNode(
                RenderNodeType.METRIC_LIST,
                props={"class": "mc-v2-values"},
                children=(
                    _metric(i18n.text("column.oos_profit_factor"), f"{item.profit_factor:.2f}"),
                    _metric(i18n.text("column.expectancy_bps"), f"{item.expectancy_bps:.2f} б.п."),
                    _metric(i18n.text("column.oos_research_trades"), str(item.oos_trades)),
                    _metric(i18n.text("column.coverage"), f"{item.coverage_pct:.0f}%"),
                    _metric(i18n.text("column.market_regime"), i18n.text(f"market.regime.{_resource_code(item.regime)}")),
                    _metric(i18n.text("column.market_session"), i18n.text(f"market.session.{_resource_code(item.session)}")),
                ),
            ),
            RenderNode(RenderNodeType.BADGE, props={"class": "mc-v2-trust-badge"}, text=item.verdict),
        ),
    )


def render_control_center_v2(
    vm: ControlCenterV2ViewModel,
    locale_code: str = "ru",
    theme_code: str = "DEFAULT",
) -> RenderDocument:
    i18n = UiI18nResolverV1(locale_code=locale_code)
    theme = ThemeResolverV1().resolve(theme_code)
    compact_grid_style = (
        "grid-template-columns:repeat(auto-fit,minmax("
        f"{_theme_px(theme, 'CONTROL_KPI_MIN_WIDTH')},1fr));"
        f"gap:{_theme_px(theme, 'CONTROL_GRID_GAP')};"
    )
    compact_card_style = (
        "grid-column:auto;"
        f"min-height:{_theme_px(theme, 'CONTROL_CARD_MIN_HEIGHT')};"
        f"padding:{_theme_px(theme, 'CONTROL_CARD_PADDING')};"
        f"border-radius:{_theme_px(theme, 'CONTROL_CARD_RADIUS')};"
    )
    compact_kpi_style = (
        f"font-size:{_theme_px(theme, 'CONTROL_KPI_FONT_SIZE')};"
        f"font-weight:{int(theme.get('CONTROL_KPI_FONT_WEIGHT'))};"
    )
    navigation_card_style = (
        "grid-column:auto;"
        f"min-height:{_theme_px(theme, 'CONTROL_NAV_CARD_MIN_HEIGHT')};"
        f"padding:{_theme_px(theme, 'CONTROL_NAV_CARD_PADDING')};"
        f"border-radius:{_theme_px(theme, 'CONTROL_CARD_RADIUS')};"
    )
    navigation = RenderNode(
        RenderNodeType.SECTION,
        props={"class": "mc-v2-section", "data-section": "CONTROL"},
        children=(
            _title(i18n.text("research.control.navigation.title"), 2),
            RenderNode(RenderNodeType.SUBTITLE, text=i18n.text("research.control.navigation.subtitle")),
            RenderNode(
                RenderNodeType.GRID,
                props={"class": "mc-v2-grid", "style": "grid-template-columns:repeat(auto-fit,minmax(180px,1fr))"},
                children=(
                    RenderNode(RenderNodeType.CARD, props={"class": "mc-v2-card", "style": navigation_card_style, "href": "/", "aria_label": i18n.text("button.home"), "data-card": "ACTION", "data-status": "OK"}, children=(_title(i18n.text("research.control.navigation.home"), 3),)),
                    RenderNode(RenderNodeType.CARD, props={"class": "mc-v2-card", "style": navigation_card_style, "href": "/workspace-v2/portfolio", "aria_label": i18n.text("portfolio.title"), "data-card": "ACTION", "data-status": "OK"}, children=(_title(i18n.text("research.control.navigation.portfolio"), 3),)),
                ),
            ),
        ),
    )

    traffic = RenderNode(
        RenderNodeType.SECTION,
        props={"class": "mc-v2-section", "id": "state", "data-section": "OBSERVATION"},
        children=(
            _title(i18n.text("research.control.state.title"), 2),
            RenderNode(RenderNodeType.SUBTITLE, text=i18n.text("research.control.state.subtitle")),
            RenderNode(
                RenderNodeType.GRID,
                props={"class": "mc-v2-grid", "style": "grid-template-columns:repeat(auto-fit,minmax(190px,1fr))"},
                children=tuple(
                    RenderNode(
                        RenderNodeType.CARD,
                        props={"class": "mc-v2-card", "style": compact_card_style, "href": light.target, "aria_label": light.label, "data-card": "ACTION", "data-status": light.status},
                        children=(_title(light.label, 3), RenderNode(RenderNodeType.TEXT, props={"class": "mc-v2-kpi-value", "style": compact_kpi_style}, text=light.detail)),
                    )
                    for light in vm.traffic_lights
                ),
            ),
        ),
    )

    shadow = vm.shadow_summary
    shadow_section = RenderNode(
        RenderNodeType.SECTION,
        props={"class": "mc-v2-section", "data-section": "SHADOW"},
        children=(
            _title(i18n.text("research.shadow.title"), 2),
            RenderNode(
                RenderNodeType.SUBTITLE,
                text=(
                    i18n.text("research.shadow.subtitle.archived" if shadow.get("reporting_is_archived") else "research.shadow.subtitle.active")
                ),
            ),
            RenderNode(
                RenderNodeType.GRID,
                props={"class": "mc-v2-grid"},
                children=tuple(
                    RenderNode(
                        RenderNodeType.CARD,
                        props={"class": "mc-v2-card", "data-card": "KPI", "data-status": status},
                        children=(_title(label, 3), RenderNode(RenderNodeType.TEXT, props={"class": "mc-v2-kpi-value"}, text=value)),
                    )
                    for label, value, status in (
                        (i18n.text("research.shadow.active_cohort"), i18n.text("status.accumulating" if int(shadow.get("active_observations") or 0) == 0 else "status.observation"), "WARNING"),
                        (i18n.text("research.shadow.new_observations"), str(int(shadow.get("active_observations") or 0)), "WARNING"),
                        (i18n.text("research.shadow.metric_source"), i18n.text("research.shadow.archived_baseline" if shadow.get("reporting_is_archived") else "research.shadow.active_baseline"), "WARNING" if shadow.get("reporting_is_archived") else "OK"),
                        (i18n.text("research.shadow.readiness"), i18n.text("status.ready_to_open" if shadow.get("guard_check_status") == "READY_FOR_SHADOW_OPEN" else "status.blocked"), "OK" if shadow.get("guard_check_status") == "READY_FOR_SHADOW_OPEN" else "BLOCKED"),
                        (i18n.text("research.shadow.total"), str(int(shadow.get("total") or 0)), "WARNING"),
                        (i18n.text("research.shadow.awaiting_entry"), str(int(shadow.get("pending") or 0)), "WARNING"),
                        (i18n.text("research.shadow.open"), str(int(shadow.get("open") or 0)), "WARNING"),
                        (i18n.text("research.shadow.closed"), str(int(shadow.get("closed") or 0)), "OK"),
                        (i18n.text("research.shadow.all_unique_paths"), f"{float(shadow.get('net_pnl') or 0):.2f}", "WARNING"),
                        (i18n.text("research.shadow.eligible_families"), str(int(shadow.get("eligible_families") or 0)), "OK" if int(shadow.get("eligible_families") or 0) > 0 else "WARNING"),
                        (i18n.text("research.shadow.eligible_paths"), str(int(shadow.get("eligible_closed") or 0)), "OK"),
                        (i18n.text("research.shadow.eligible_result"), f"{float(shadow.get('eligible_net_pnl') or 0):.2f}", "OK" if float(shadow.get("eligible_net_pnl") or 0) > 0 else "WARNING"),
                        (i18n.text("research.shadow.quality_pending"), str(int(shadow.get("quality_pending_families") or 0)), "WARNING"),
                        (i18n.text("research.shadow.pending_paths"), str(int(shadow.get("quality_pending_closed") or 0)), "WARNING"),
                        (i18n.text("research.shadow.pending_result"), f"{float(shadow.get('quality_pending_net_pnl') or 0):.2f}", "WARNING"),
                        (i18n.text("research.shadow.exploratory_families"), str(int(shadow.get("exploratory_families") or 0)), "WARNING"),
                        (i18n.text("research.shadow.exploratory_paths"), str(int(shadow.get("exploratory_closed") or 0)), "WARNING"),
                        (i18n.text("research.shadow.exploratory_result"), f"{float(shadow.get('exploratory_net_pnl') or 0):.2f}", "BLOCKED" if float(shadow.get("exploratory_net_pnl") or 0) < 0 else "WARNING"),
                        (i18n.text("research.shadow.atr_trailing"), str(int(shadow.get("trailing_total") or 0)), "WARNING"),
                        (i18n.text("research.shadow.trailing_triggered"), str(int(shadow.get("trailing_exits") or 0)), "OK"),
                        (i18n.text("research.shadow.trailing_result"), f"{float(shadow.get('trailing_net_pnl') or 0):.2f}", "OK" if float(shadow.get("trailing_net_pnl") or 0) >= 0 else "BLOCKED"),
                        (i18n.text("research.shadow.violations"), str(int(shadow.get("unsafe") or 0) + int(shadow.get("trailing_unsafe") or 0)), "OK" if int(shadow.get("unsafe") or 0) + int(shadow.get("trailing_unsafe") or 0) == 0 else "BLOCKED"),
                    )
                ),
            ),
        ),
    )

    funnel = RenderNode(
        RenderNodeType.SECTION,
        props={"class": "mc-v2-section", "id": "signal-funnel", "data-section": "FUNNEL"},
        children=(
            _title("Воронка сигналов", 2),
            RenderNode(
                RenderNodeType.SUBTITLE,
                text=("Стадии сопоставимы" if vm.funnel_comparable else "Источники стадий пока несопоставимы"),
            ),
            RenderNode(
                RenderNodeType.GRID,
                props={"class": "mc-v2-grid", "style": compact_grid_style},
                children=tuple(
                    RenderNode(
                        RenderNodeType.CARD,
                        props={"class": "mc-v2-card", "style": compact_card_style, "data-card": "KPI", "data-status": stage.status},
                        children=(
                            _title(stage.label, 3),
                            RenderNode(RenderNodeType.TEXT, props={"class": "mc-v2-kpi-value", "style": compact_kpi_style}, text=str(stage.count)),
                            RenderNode(RenderNodeType.TEXT, props={"class": "mc-v2-card-detail"}, text=stage.conversion),
                        ),
                    )
                    for stage in vm.funnel_stages
                ),
            ),
        ),
    )

    recommendations = RenderNode(
        RenderNodeType.SECTION,
        props={"class": "mc-v2-section", "id": "recommendations", "data-section": "ALERTS"},
        children=(
            _title("Причины и действия", 2),
            RenderNode(RenderNodeType.SUBTITLE, text="Сначала устраняются самые частые подтверждённые причины"),
            data_table_node(
                (
                    DataTableColumn("reason", i18n.text("column.loss_reason")),
                    DataTableColumn("count", i18n.text("column.event_count")),
                    DataTableColumn("action", i18n.text("column.recommended_action")),
                    DataTableColumn("status", i18n.text("column.status")),
                ),
                tuple(
                    {
                        "reason": reason.label,
                        "count": reason.count,
                        "action": reason.action,
                        "status": i18n.text(
                            f"status.{_resource_code(reason.status)}"
                            if reason.action_target
                            else "status.execution_section_missing"
                        ),
                        "_activation_target": reason.action_target,
                        "_aria_label": i18n.text("research.recommendation.execute_aria").format(reason=reason.label),
                        "_progress_label": i18n.text("research.recommendation.progress").format(reason=reason.label),
                        "_progress_complete_label": i18n.text("research.recommendation.progress_complete"),
                        "_confirmation_options": _recommendation_options(vm, reason.code, i18n),
                        "_confirmation_title": i18n.text("research.recommendation.confirm_title"),
                        "_confirmation_label": i18n.text("research.recommendation.confirm"),
                        "_status": reason.status if reason.action_target else "BLOCKED",
                    }
                    for reason in vm.loss_reasons
                ),
            ),
            RenderNode(
                RenderNodeType.ACTION,
                props={"class": "mc-v2-button", "href": "/workspace-v2/control-center/edge-oos/signal-funnel", "action_code": "OPEN", "aria_label": "Открыть полную воронку"},
                text="Открыть полную воронку",
            ),
        ),
    )

    summary = vm.relationship_summary
    volatility_section = RenderNode(
        RenderNodeType.SECTION,
        props={"class": "mc-v2-section", "id": "volatility-analysis", "data-section": "RESEARCH"},
        children=(
            _title(i18n.text("research.volatility.title"), 2),
            RenderNode(RenderNodeType.SUBTITLE, text=i18n.text("research.volatility.subtitle")),
            data_table_node(
                (
                    DataTableColumn("regime", i18n.text("column.market_regime")),
                    DataTableColumn("trials", i18n.text("column.trials")),
                    DataTableColumn("trades", i18n.text("column.oos_research_trades")),
                    DataTableColumn("pf", i18n.text("column.oos_profit_factor")),
                    DataTableColumn("expectancy", i18n.text("column.expectancy_bps")),
                    DataTableColumn("passed", i18n.text("column.passed")),
                ),
                tuple({
                    "regime": i18n.text(f"market.regime.{_resource_code(str(row.get('regime_group') or 'unknown'))}"),
                    "trials": int(row.get("trials") or 0), "trades": int(row.get("oos_trades") or 0),
                    "pf": f"{float(row.get('profit_factor') or 0):.3f}",
                    "expectancy": f"{float(row.get('expectancy_bps') or 0):.3f}",
                    "passed": int(row.get("passed") or 0),
                } for row in vm.volatility_analysis),
            ),
        ),
    )

    risk_section = RenderNode(
        RenderNodeType.SECTION,
        props={"class": "mc-v2-section", "id": "risk-analysis", "data-section": "RISK"},
        children=(
            _title(i18n.text("research.risk.title"), 2),
            RenderNode(RenderNodeType.SUBTITLE, text=i18n.text("research.risk.subtitle")),
            data_table_node(
                (
                    DataTableColumn("symbol", i18n.text("column.instrument")),
                    DataTableColumn("strategy", i18n.text("column.strategy")),
                    DataTableColumn("risk", i18n.text("column.risk_score")),
                    DataTableColumn("position", i18n.text("column.position_risk")),
                    DataTableColumn("exposure", i18n.text("column.exposure_risk")),
                    DataTableColumn("decision", i18n.text("column.decision")),
                    DataTableColumn("paper", i18n.text("column.paper_allowed")),
                ),
                tuple({
                    "symbol": row.get("symbol") or "—", "strategy": row.get("strategy_family") or "—",
                    "risk": f"{float(row.get('risk_score') or 0):.3f}",
                    "position": f"{float(row.get('position_risk_score') or 0):.3f}",
                    "exposure": f"{float(row.get('exposure_risk_score') or 0):.3f}",
                    "decision": row.get("risk_decision_code") or "—",
                    "paper": i18n.text("status.allowed" if row.get("ready_for_paper") else "status.blocked"),
                } for row in vm.risk_analysis),
            ),
        ),
    )

    entry_section = RenderNode(
        RenderNodeType.SECTION,
        props={"class": "mc-v2-section", "id": "entry-analysis", "data-section": "RESEARCH"},
        children=(
            _title(i18n.text("research.entry.title"), 2),
            RenderNode(RenderNodeType.SUBTITLE, text=i18n.text("research.entry.subtitle")),
            data_table_node(
                (
                    DataTableColumn("strategy", i18n.text("column.strategy")),
                    DataTableColumn("symbol", i18n.text("column.instrument")),
                    DataTableColumn("parameters", i18n.text("column.parameters")),
                    DataTableColumn("trades", i18n.text("column.oos_research_trades")),
                    DataTableColumn("pf", i18n.text("column.oos_profit_factor")),
                    DataTableColumn("folds", i18n.text("column.folds")),
                    DataTableColumn("verdict", i18n.text("column.verdict")),
                    DataTableColumn("solution", i18n.text("column.solution")),
                ),
                tuple({
                    "strategy": i18n.text(f"strategy.{_resource_code(str(row.get('strategy_code') or 'unknown'))}"), "symbol": row.get("symbol") or "—",
                    "parameters": _parameter_text(row.get("parameter_json") or {}, i18n),
                    "trades": int(row.get("oos_trades") or 0), "pf": f"{float(row.get('oos_profit_factor') or 0):.3f}",
                    "folds": f"{int(row.get('folds_passed') or 0)}/{int(row.get('folds_total') or 0)}",
                    "verdict": i18n.text(f"status.{_resource_code(str(row.get('verdict_code') or 'unknown'))}"),
                    "solution": i18n.text("research.solution.promote" if row.get("promotion_allowed") else "research.solution.collect_evidence"),
                } for row in vm.entry_analysis),
            ),
        ),
    )

    execution_section = RenderNode(
        RenderNodeType.SECTION,
        props={"class": "mc-v2-section", "id": "execution-quality", "data-section": "EXECUTION"},
        children=(
            _title(i18n.text("research.execution.title"), 2),
            RenderNode(RenderNodeType.SUBTITLE, text=i18n.text("research.execution.subtitle")),
            data_table_node(
                (
                    DataTableColumn("mode", i18n.text("column.mode")),
                    DataTableColumn("opened", i18n.text("column.positions_opened")),
                    DataTableColumn("stop", i18n.text("column.stops_placed")),
                    DataTableColumn("active", i18n.text("column.trailing_active")),
                    DataTableColumn("improved", i18n.text("column.stops_improved")),
                    DataTableColumn("lock", i18n.text("column.profit_locks")),
                    DataTableColumn("take", i18n.text("column.take_profits")),
                    DataTableColumn("closed", i18n.text("column.positions_closed")),
                    DataTableColumn("quotes", i18n.text("column.quotes_quality")),
                ),
                tuple({
                    "mode": i18n.text(f"research.execution.mode.{_resource_code(str(row.get('mode') or 'unknown'))}"), "opened": int(row.get("positions_opened") or 0),
                    "stop": int(row.get("stops_placed") or 0), "active": int(row.get("trailing_active") or 0),
                    "improved": int(row.get("stops_improved") or 0), "lock": int(row.get("profit_locks") or 0),
                    "take": int(row.get("take_profits") or 0), "closed": int(row.get("positions_closed") or 0),
                    "quotes": i18n.text("status.verified" if row.get("quotes_verified") else "status.not_verified"),
                    "_activation_target": "#execution-quality",
                    "_aria_label": i18n.text("execution.funnel.execute_aria"),
                    "_progress_label": i18n.text("execution.funnel.progress"),
                    "_progress_complete_label": i18n.text("research.recommendation.progress_complete"),
                    "_confirmation_options": _recommendation_options(vm, "EXECUTION", i18n),
                    "_confirmation_title": i18n.text("execution.funnel.confirm_title"),
                    "_confirmation_label": i18n.text("research.recommendation.confirm"),
                    "_status": "OK" if row.get("quotes_verified") else "WARNING",
                } for row in vm.execution_quality),
            ),
        ),
    )

    market_section = RenderNode(
        RenderNodeType.SECTION,
        props={"class": "mc-v2-section", "id": "market-prerequisites", "data-section": "OBSERVATION"},
        children=(
            _title(i18n.text("research.market.title"), 2),
            RenderNode(RenderNodeType.SUBTITLE, text=i18n.text("research.market.subtitle")),
            data_table_node(
                (DataTableColumn("symbol", i18n.text("column.instrument")), DataTableColumn("timeframe", "TF"), DataTableColumn("bars", i18n.text("column.bars")), DataTableColumn("days", i18n.text("column.days")), DataTableColumn("age", i18n.text("column.age")), DataTableColumn("coverage", i18n.text("column.coverage")), DataTableColumn("status", i18n.text("column.status")), DataTableColumn("reason", i18n.text("column.loss_reason")), DataTableColumn("solution", i18n.text("column.solution"))),
                tuple({"symbol": r.get("symbol"), "timeframe": r.get("timeframe"), "bars": r.get("bars"), "days": r.get("trading_days"), "age": f"{float(r.get('latest_age_hours') or 0):.1f} ч", "coverage": f"{float(r.get('regime_coverage_ratio') or 0)*100:.0f}%", "status": i18n.text("status.ready" if r.get("factory_status") == "READY" else "status.blocked"), "reason": _quality_reason_text(r, i18n), "solution": i18n.text("research.solution.use_ready" if r.get("factory_status") == "READY" else "research.solution.refresh_data"), "_status": "OK" if r.get("factory_status") == "READY" else "BLOCKED"} for r in vm.market_prerequisites),
            ),
        ),
    )
    exit_section = RenderNode(
        RenderNodeType.SECTION,
        props={"class": "mc-v2-section", "id": "exit-analysis", "data-section": "RESEARCH"},
        children=(
            _title(i18n.text("research.exit.title"), 2), RenderNode(RenderNodeType.SUBTITLE, text=i18n.text("research.exit.subtitle")),
            data_table_node(
                (DataTableColumn("policy", i18n.text("column.policy")), DataTableColumn("variants", i18n.text("column.trials")), DataTableColumn("closed", i18n.text("column.closed")), DataTableColumn("hold", i18n.text("column.hold_minutes")), DataTableColumn("pnl", i18n.text("column.net_pnl")), DataTableColumn("trailing", i18n.text("column.trailing_exits")), DataTableColumn("solution", i18n.text("column.solution"))),
                tuple({"policy": r.get("policy_code"), "variants": r.get("variants"), "closed": r.get("closed"), "hold": f"{float(r.get('avg_hold_minutes') or 0):.1f}", "pnl": f"{float(r.get('net_pnl') or 0):.2f}", "trailing": r.get("trailing_exits"), "solution": i18n.text("research.solution.observe_exit" if int(r.get("closed") or 0) == 0 else "research.solution.compare_exit")} for r in vm.exit_analysis),
            ),
        ),
    )
    block_section = RenderNode(
        RenderNodeType.SECTION,
        props={"class": "mc-v2-section", "id": "block-analysis", "data-section": "ALERTS"},
        children=(
            _title(i18n.text("research.block.title"), 2), RenderNode(RenderNodeType.SUBTITLE, text=i18n.text("research.block.subtitle")),
            data_table_node(
                (DataTableColumn("reason", i18n.text("column.loss_reason")), DataTableColumn("count", i18n.text("column.event_count")), DataTableColumn("source", i18n.text("column.source")), DataTableColumn("solution", i18n.text("column.solution"))),
                tuple({"reason": r.get("reason_value"), "count": r.get("rows_total"), "source": f"{r.get('source_table')}.{r.get('reason_column')}", "solution": i18n.text("research.solution.keep_blocked")} for r in vm.block_analysis),
            ),
        ),
    )

    relationship_section = RenderNode(
        RenderNodeType.SECTION,
        props={"class": "mc-v2-section", "id": "relationship-factory", "data-section": "RESEARCH"},
        children=(
            _title(i18n.text("research.relationship_factory.title"), 2),
            RenderNode(
                RenderNodeType.SUBTITLE,
                text=i18n.text("research.relationship_factory.summary").format(
                    relationships=int(summary.get("relationships") or 0),
                    trials=int(summary.get("trials") or 0),
                    passed=int(summary.get("passed") or 0),
                ),
            ),
            data_table_node(
                (
                    DataTableColumn("family", i18n.text("column.relationship_family")),
                    DataTableColumn("relationship", i18n.text("column.relationship")),
                    DataTableColumn("profit_factor", i18n.text("column.oos_profit_factor")),
                    DataTableColumn("expectancy", i18n.text("column.expectancy_bps")),
                    DataTableColumn("oos_trades", i18n.text("column.oos_research_trades")),
                    DataTableColumn("coverage", i18n.text("column.coverage")),
                    DataTableColumn("regime", i18n.text("column.market_regime")),
                    DataTableColumn("session", i18n.text("column.market_session")),
                    DataTableColumn("verdict", i18n.text("column.verdict")),
                ),
                tuple(
                    {
                        "family": item.family,
                        "relationship": f"{item.source} → {item.target}",
                        "profit_factor": f"{item.profit_factor:.2f}",
                        "expectancy": f"{item.expectancy_bps:.2f}",
                        "oos_trades": item.oos_trades,
                        "coverage": f"{item.coverage_pct:.0f}%",
                        "regime": i18n.text(f"market.regime.{_resource_code(item.regime)}"),
                        "session": i18n.text(f"market.session.{_resource_code(item.session)}"),
                        "verdict": i18n.text(f"status.{_resource_code(item.verdict)}"),
                    }
                    for item in vm.relationships
                ),
            ),
        ),
    )

    return RenderDocument(
        root=RenderNode(
            RenderNodeType.WORKSPACE,
            props={"class": "mc-v2-shell"},
            children=(
                RenderNode(
                    RenderNodeType.PAGE,
                    props={"class": "mc-v2-page", "style": "box-sizing:border-box;padding-left:0"},
                    children=(
                        _title(vm.title, 1),
                        RenderNode(RenderNodeType.HEADER, props={"class": "mc-v2-header"}, text=vm.subtitle),
                        navigation,
                        traffic,
                        shadow_section,
                        funnel,
                        recommendations,
                        volatility_section,
                        risk_section,
                        entry_section,
                        execution_section,
                        market_section,
                        exit_section,
                        block_section,
                        relationship_section,
                    ),
                ),
            ),
        )
    )
