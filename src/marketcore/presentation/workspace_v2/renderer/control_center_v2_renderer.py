from __future__ import annotations

from marketcore.presentation.render_tree.node_types import RenderNodeType
from marketcore.presentation.render_tree.render_document import RenderDocument
from marketcore.presentation.render_tree.render_node import RenderNode
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


def render_control_center_v2(vm: ControlCenterV2ViewModel) -> RenderDocument:
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
                    RenderNode(RenderNodeType.CARD, props={"class": "mc-v2-card", "style": "grid-column:auto;min-height:72px", "href": "/workspace-v2/control-center/edge-oos/legacy", "aria_label": "Полный экран", "data-card": "ACTION", "data-status": "WARNING"}, children=(_title("◫ Полный экран", 3),)),
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
                props={"class": "mc-v2-grid", "style": "grid-template-columns:repeat(auto-fit,minmax(170px,1fr))"},
                children=tuple(
                    RenderNode(
                        RenderNodeType.CARD,
                        props={"class": "mc-v2-card", "style": "grid-column:auto;min-height:105px", "data-card": "KPI", "data-status": status},
                        children=(_title(label, 3), RenderNode(RenderNodeType.TEXT, props={"class": "mc-v2-kpi-value"}, text=value)),
                    )
                    for label, value, status in (
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
                props={"class": "mc-v2-grid", "style": "grid-template-columns:repeat(auto-fit,minmax(170px,1fr))"},
                children=tuple(
                    RenderNode(
                        RenderNodeType.CARD,
                        props={"class": "mc-v2-card", "style": "grid-column:auto;min-height:112px", "data-card": "KPI", "data-status": stage.status},
                        children=(
                            _title(stage.label, 3),
                            RenderNode(RenderNodeType.TEXT, props={"class": "mc-v2-kpi-value"}, text=str(stage.count)),
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
            RenderNode(
                RenderNodeType.GRID,
                props={"class": "mc-v2-grid", "style": "grid-template-columns:repeat(auto-fit,minmax(260px,1fr))"},
                children=tuple(
                    RenderNode(
                        RenderNodeType.CARD,
                        props={"class": "mc-v2-card", "style": "grid-column:auto;min-height:0", "data-card": "ALERT", "data-status": reason.status},
                        children=(
                            _title(reason.label, 3),
                            RenderNode(RenderNodeType.TEXT, props={"class": "mc-v2-kpi-value"}, text=str(reason.count)),
                            RenderNode(RenderNodeType.TEXT, props={"class": "mc-v2-card-detail"}, text=reason.action),
                        ),
                    )
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
            _title("Фабрика связей", 2),
            RenderNode(RenderNodeType.SUBTITLE, text=f"{int(summary.get('relationships') or 0)} связей · {int(summary.get('trials') or 0)} проверок · PASS {int(summary.get('passed') or 0)}"),
            RenderNode(RenderNodeType.GRID, props={"class": "mc-v2-grid", "style": "grid-template-columns:repeat(auto-fit,minmax(260px,1fr))"}, children=tuple(_relationship_card(item) for item in vm.relationships)),
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
