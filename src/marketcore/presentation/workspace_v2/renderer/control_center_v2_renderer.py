from __future__ import annotations

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


def _theme_px(theme: ThemeModel, property_code: str) -> str:
    value = theme.get(property_code)
    if not value:
        raise RuntimeError(f"THEME_PROPERTY_NOT_FOUND:{property_code}")
    return f"{int(value)}px"


def _relationship_card(item: RelationshipCandidateV2) -> RenderNode:
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
                    _metric("OOS PF", f"{item.profit_factor:.2f}"),
                    _metric("Ожидание", f"{item.expectancy_bps:.2f} б.п."),
                    _metric("Сделки", str(item.oos_trades)),
                    _metric("Покрытие", f"{item.coverage_pct:.0f}%"),
                    _metric("Режим", item.regime),
                    _metric("Сессия", item.session),
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
    navigation = RenderNode(
        RenderNodeType.SECTION,
        props={"class": "mc-v2-section", "data-section": "CONTROL"},
        children=(
            _title("Рабочие разделы", 2),
            RenderNode(RenderNodeType.SUBTITLE, text="Короткие переходы без запуска фоновых задач"),
            RenderNode(
                RenderNodeType.GRID,
                props={"class": "mc-v2-grid", "style": "grid-template-columns:repeat(auto-fit,minmax(180px,1fr))"},
                children=(
                    RenderNode(RenderNodeType.CARD, props={"class": "mc-v2-card", "style": "grid-column:auto;min-height:72px", "href": "/", "aria_label": "Главная", "data-card": "ACTION", "data-status": "OK"}, children=(_title("⌂ Главная", 3),)),
                    RenderNode(RenderNodeType.CARD, props={"class": "mc-v2-card", "style": "grid-column:auto;min-height:72px", "href": "/workspace-v2/portfolio", "aria_label": "Портфель", "data-card": "ACTION", "data-status": "OK"}, children=(_title("▦ Портфель", 3),)),
                ),
            ),
        ),
    )

    traffic = RenderNode(
        RenderNodeType.SECTION,
        props={"class": "mc-v2-section", "data-section": "OBSERVATION"},
        children=(
            _title("Состояние", 2),
            RenderNode(RenderNodeType.SUBTITLE, text="Зелёный — подтверждено · жёлтый — наблюдение · красный — запрет"),
            RenderNode(
                RenderNodeType.GRID,
                props={"class": "mc-v2-grid", "style": "grid-template-columns:repeat(auto-fit,minmax(190px,1fr))"},
                children=tuple(
                    RenderNode(
                        RenderNodeType.CARD,
                        props={"class": "mc-v2-card", "style": "grid-column:auto;min-height:118px", "href": light.target, "aria_label": light.label, "data-card": "ACTION", "data-status": light.status},
                        children=(_title(light.label, 3), RenderNode(RenderNodeType.TEXT, props={"class": "mc-v2-kpi-value"}, text=light.detail)),
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
            _title("Shadow-сделки", 2),
            RenderNode(RenderNodeType.SUBTITLE, text="Без брокерских заявок · только новые forward-наблюдения"),
            RenderNode(
                RenderNodeType.GRID,
                props={"class": "mc-v2-grid", "style": compact_grid_style},
                children=tuple(
                    RenderNode(
                        RenderNodeType.CARD,
                        props={"class": "mc-v2-card", "style": compact_card_style, "data-card": "KPI", "data-status": status},
                        children=(_title(label, 3), RenderNode(RenderNodeType.TEXT, props={"class": "mc-v2-kpi-value", "style": compact_kpi_style}, text=value)),
                    )
                    for label, value, status in (
                        ("Готовность", "Готово к открытию" if shadow.get("guard_check_status") == "READY_FOR_SHADOW_OPEN" else "Заблокировано", "OK" if shadow.get("guard_check_status") == "READY_FOR_SHADOW_OPEN" else "BLOCKED"),
                        ("Всего", str(int(shadow.get("total") or 0)), "WARNING"),
                        ("Ожидают вход", str(int(shadow.get("pending") or 0)), "WARNING"),
                        ("Открыты", str(int(shadow.get("open") or 0)), "WARNING"),
                        ("Закрыты", str(int(shadow.get("closed") or 0)), "OK"),
                        ("Результат", f"{float(shadow.get('net_pnl') or 0):.2f}", "OK" if float(shadow.get("net_pnl") or 0) >= 0 else "BLOCKED"),
                        ("ATR-трейлинг", str(int(shadow.get("trailing_total") or 0)), "WARNING"),
                        ("Трейлинг сработал", str(int(shadow.get("trailing_exits") or 0)), "OK"),
                        ("Результат трейлинга", f"{float(shadow.get('trailing_net_pnl') or 0):.2f}", "OK" if float(shadow.get("trailing_net_pnl") or 0) >= 0 else "BLOCKED"),
                        ("Нарушения", str(int(shadow.get("unsafe") or 0) + int(shadow.get("trailing_unsafe") or 0)), "OK" if int(shadow.get("unsafe") or 0) + int(shadow.get("trailing_unsafe") or 0) == 0 else "BLOCKED"),
                    )
                ),
            ),
        ),
    )

    funnel = RenderNode(
        RenderNodeType.SECTION,
        props={"class": "mc-v2-section", "data-section": "FUNNEL"},
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
        props={"class": "mc-v2-section", "data-section": "ALERTS"},
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
                        "status": i18n.text(f"status.{_resource_code(reason.status)}"),
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
    relationship_section = RenderNode(
        RenderNodeType.SECTION,
        props={"class": "mc-v2-section", "data-section": "RESEARCH"},
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
                        relationship_section,
                    ),
                ),
            ),
        )
    )
