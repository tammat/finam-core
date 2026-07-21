from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from numbers import Number
from typing import Any, Iterable

from marketcore.presentation.render_tree.v2 import (
    ActionKindV2,
    RenderActionV2,
    RenderContentV2,
    RenderDocumentV2,
    RenderNodeStateV2,
    RenderNodeTypeV2,
    RenderNodeV2,
    validate_render_document_v2,
)
from marketcore.presentation.workspace_v2.viewmodel.control_center_v2_viewmodel import (
    ControlCenterV2ViewModel,
)


def _code(value: object) -> str:
    normalized = re.sub(r"[^a-z0-9]+", ".", str(value).strip().lower()).strip(".")
    return normalized or "unknown"


def _message_code(value: object) -> str:
    if isinstance(value, (list, tuple, set)):
        return ",".join(str(item).strip().lower() for item in value)
    return str(value).strip().lower()


def _utc(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _display_value(column_code: str, value: Any) -> tuple[Any, str]:
    normalized = column_code.lower()
    if value == "стратегия_заблокирована_по_статистике":
        return "STRATEGY_BLOCKED_BY_STATISTICS", "DOMAIN_CODE"
    if isinstance(value, datetime):
        return value, "DATETIME"
    if isinstance(value, bool):
        return value, "BOOLEAN"
    if isinstance(value, Number):
        if "_hours" in normalized or normalized.endswith("hours"):
            return int(Decimal(str(value)) * Decimal(3600)), "DURATION_HM"
        if "_minutes" in normalized or normalized.endswith("minutes"):
            return int(Decimal(str(value)) * Decimal(60)), "DURATION_HM"
        if any(marker in normalized for marker in ("_pct", "percent", "coverage", "conversion")):
            return value, "PERCENT"
        if any(marker in normalized for marker in ("pnl", "profit", "loss", "cost", "fee")):
            return value, "MONEY_RUB"
        if isinstance(value, int):
            return value, "INTEGER"
        return value, "DECIMAL"
    return ("NO_DATA" if value is None else value), "DOMAIN_VALUE"


def _content_node(
    node_type: RenderNodeTypeV2,
    node_id: str,
    *,
    message_key: str | None = None,
    message_args: dict[str, Any] | None = None,
    value: Any = None,
    format_code: str | None = None,
    level_code: str | None = None,
    column_code: str | None = None,
) -> RenderNodeV2:
    return RenderNodeV2(
        node_type=node_type,
        node_id=node_id,
        content=RenderContentV2(
            message_key=message_key,
            message_args=message_args,
            value=value,
            format_code=format_code,
            level_code=level_code,
            column_code=column_code,
        ),
    )


def _source_as_of(rows: Iterable[dict[str, Any]]) -> datetime | None:
    candidates = [
        timestamp
        for row in rows
        for value in row.values()
        if (timestamp := _utc(value)) is not None
    ]
    return max(candidates) if candidates else None


_FUNNEL_STAGE_CONTAINER = {
    "RESEARCH": "container.research",
    "CANDIDATE": "container.research",
    "VALIDATED_EDGE": "container.edge",
    "OOS": "container.edge",
    "FORWARD": "container.intraday",
    "SHADOW": "container.intraday",
    "PAPER": "container.intraday",
    "RUNTIME": "container.intraday",
    "LIVE": "container.intraday",
    "PROFIT": "container.capital",
}


def _table_row_action(section_code: str, row: dict[str, Any]) -> RenderActionV2 | None:
    if section_code == "swing_lifecycle":
        return RenderActionV2(
            action_id=f"swing.details.{_code(row.get('symbol') or 'candidate')}.{row.get('priority') or 0}",
            action_kind=ActionKindV2.NAVIGATE,
            target_id="container.edge",
        )
    if section_code == "block":
        return RenderActionV2(
            action_id="research.edge_search.run",
            action_kind=ActionKindV2.COMMAND,
            target_id=str(row.get("blocking_rule") or "block-review"),
            command_code="RESEARCH.RUN_EDGE_SEARCH",
            policy_class="RESEARCH_MAINTENANCE",
            reversible=True,
            rollback_code="RESEARCH.CANCEL_PENDING_REQUEST",
            idempotency_key="client.request",
        )
    if section_code != "funnel":
        return None
    stage_code = str(row.get("stage_code") or "").strip().upper()
    reason_code = str(row.get("reason_code") or "").strip().upper()
    if row.get("pass_rate_pct") is None and reason_code != "INITIAL_STAGE":
        return RenderActionV2(
            action_id="research.request.refresh",
            action_kind=ActionKindV2.COMMAND,
            target_id=stage_code,
            command_code="RESEARCH.REQUEST_REFRESH",
            policy_class="RESEARCH_MAINTENANCE",
            reversible=True,
            rollback_code="RESEARCH.CANCEL_PENDING_REQUEST",
            idempotency_key="client.request",
        )
    target_id = _FUNNEL_STAGE_CONTAINER.get(stage_code)
    if target_id is None:
        return None
    return RenderActionV2(
        action_id=f"navigation.funnel.{_code(stage_code)}",
        action_kind=ActionKindV2.NAVIGATE,
        target_id=target_id,
    )


def _table_section(
    section_code: str,
    rows: tuple[dict[str, Any], ...],
    *,
    status_code: str = "WARNING",
) -> RenderNodeV2:
    section_id = f"control.section.{section_code}"
    columns: list[str] = []
    for row in rows:
        for column in row:
            if str(column) not in columns:
                columns.append(str(column))

    header = RenderNodeV2(
        RenderNodeTypeV2.TABLE_ROW,
        f"{section_id}.header",
        children=tuple(
            _content_node(
                RenderNodeTypeV2.TABLE_HEADER_CELL,
                f"{section_id}.header.{index}",
                message_key=f"column.{_code(column)}",
                column_code=column,
            )
            for index, column in enumerate(columns, start=1)
        ),
    )

    body_rows: list[RenderNodeV2] = []
    for row_index, row in enumerate(rows, start=1):
        cells: list[RenderNodeV2] = []
        for column_index, column in enumerate(columns, start=1):
            raw_value = row.get(column)
            display_value, format_code = _display_value(column, raw_value)
            normalized_column = column.lower()
            message_args: dict[str, Any] | None = None
            is_localized_code = (
                normalized_column == "status"
                or normalized_column.endswith("_status")
                or normalized_column in {
                    "freshness_code", "quality_code", "verdict_code",
                    "market_data_quality", "mode", "cohort_code",
                    "scope_code",
                }
                or any(
                    marker in normalized_column
                    for marker in (
                        "reason", "regime", "session", "strategy_code",
                        "policy_code", "recommendation_code", "decision_code",
                        "family_code", "stage_code",
                    )
                )
            )
            is_localized_code = is_localized_code and isinstance(
                raw_value, (str, list, tuple, set)
            )
            message_key = None
            if (
                section_code == "funnel"
                and normalized_column == "pass_rate_pct"
                and raw_value is None
            ):
                reason_code = _message_code(row.get("reason_code") or "not_calculated")
                message_key = f"funnel.conversion.{reason_code}"
                display_value = None
                format_code = None
            elif (
                section_code == "funnel"
                and normalized_column == "source_identity"
                and isinstance(raw_value, str)
                and raw_value.strip()
            ):
                message_key = f"funnel.source.{_message_code(raw_value)}"
                message_args = {"tooltip_value": raw_value}
                display_value = None
                format_code = None
            elif raw_value is None:
                message_key = "status.no_data"
                display_value = None
                format_code = None
            elif is_localized_code:
                message_key = (
                    "status.no_data"
                    if (
                        isinstance(raw_value, str) and not raw_value.strip()
                    ) or (
                        isinstance(raw_value, (list, tuple, set)) and not raw_value
                    )
                    else f"status.{_message_code(display_value)}"
                )
            cells.append(
                _content_node(
                    RenderNodeTypeV2.TABLE_CELL,
                    f"{section_id}.row.{row_index}.cell.{column_index}",
                    message_key=message_key,
                    message_args=message_args,
                    value=display_value,
                    format_code=format_code,
                    column_code=column,
                )
            )
        body_rows.append(
            RenderNodeV2(
                RenderNodeTypeV2.TABLE_ROW,
                f"{section_id}.row.{row_index}",
                action=_table_row_action(section_code, row),
                children=tuple(cells),
            )
        )

    section_as_of = _source_as_of(rows)
    return RenderNodeV2(
        RenderNodeTypeV2.SECTION,
        section_id,
        state=RenderNodeStateV2(
            status_code=status_code,
            freshness_code="AS_OF_REPORTED" if section_as_of else "AS_OF_UNAVAILABLE",
            source_as_of=section_as_of,
            source_identity=(f"control_center.{section_code}" if section_as_of else None),
        ),
        children=(
            _content_node(
                RenderNodeTypeV2.TITLE,
                f"{section_id}.title",
                message_key=f"research.control.section.{section_code}.title",
                level_code="SECTION",
            ),
            RenderNodeV2(
                RenderNodeTypeV2.TABLE,
                f"{section_id}.table",
                children=(
                    RenderNodeV2(
                        RenderNodeTypeV2.TABLE_HEAD,
                        f"{section_id}.table.head",
                        children=(header,),
                    ),
                    RenderNodeV2(
                        RenderNodeTypeV2.TABLE_BODY,
                        f"{section_id}.table.body",
                        children=tuple(body_rows),
                    ),
                ),
            ),
        ),
    )


def _traffic_section(view_model: ControlCenterV2ViewModel) -> RenderNodeV2:
    cards = tuple(
        RenderNodeV2(
            RenderNodeTypeV2.CARD,
            f"control.traffic.{light.code}",
            state=RenderNodeStateV2(
                status_code=light.status,
                availability_code="OBSERVATION_ONLY",
            ),
            children=(
                _content_node(
                    RenderNodeTypeV2.TITLE,
                    f"control.traffic.{light.code}.title",
                    message_key=f"research.control.traffic.{light.code}.title",
                    level_code="CARD",
                ),
                _content_node(
                    RenderNodeTypeV2.METRIC_VALUE,
                    f"control.traffic.{light.code}.value",
                    message_key=light.detail_key,
                    message_args=dict(light.detail_args),
                ),
            ),
        )
        for light in view_model.traffic_lights
    )
    return RenderNodeV2(
        RenderNodeTypeV2.SECTION,
        "control.section.traffic",
        children=(
            _content_node(
                RenderNodeTypeV2.TITLE,
                "control.section.traffic.title",
                message_key="research.control.state.title",
                level_code="SECTION",
            ),
            RenderNodeV2(RenderNodeTypeV2.GRID, "control.section.traffic.grid", children=cards),
        ),
    )


def _relationship_rows(view_model: ControlCenterV2ViewModel) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "family_code": item.family_code,
            "source": item.source,
            "target": item.target,
            "regime_code": item.regime_code,
            "session_code": item.session_code,
            "oos_trades": item.oos_trades,
            "profit_factor": item.profit_factor,
            "expectancy_bps": item.expectancy_bps,
            "coverage_pct": item.coverage_pct,
            "verdict_code": item.verdict_code,
            "status": item.status,
        }
        for item in view_model.relationships
    )


def _funnel_rows(view_model: ControlCenterV2ViewModel) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "stage_code": item.stage_code,
            "count": item.count,
            "pass_rate_pct": item.pass_rate_pct,
            "status": item.status,
            "source_identity": item.source_identity,
            "source_as_of": item.source_as_of,
            "freshness_code": item.freshness_code,
            "quality_code": item.quality_code,
            "reason_code": item.reason_code,
            "net_pnl": item.net_pnl,
            "cost_impact": item.cost_impact,
        }
        for item in view_model.funnel_stages
    )


def _loss_rows(view_model: ControlCenterV2ViewModel) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "reason_code": item.code,
            "count": item.count,
            "status": item.status,
        }
        for item in view_model.loss_reasons
    )


def _swing_rows(view_model: ControlCenterV2ViewModel) -> tuple[dict[str, Any], ...]:
    strategy_names = {
        "MOMENTUM": "Импульс",
        "REGIME_MOMENTUM": "Режимный импульс",
        "BREAKOUT": "Пробой",
        "META_BREAKOUT": "Режимный пробой",
        "INTERMARKET_LEAD_LAG": "Межрыночное опережение",
        "RELATIVE_STRENGTH": "Относительная сила",
        "SWING_EDGE_SEARCH": "Swing-поиск",
    }
    stage_names = {"OOS": "OOS", "FORWARD": "Forward", "SHADOW": "Shadow", "PAPER": "Paper"}
    return tuple(
        {
            "priority": row.get("priority"),
            "symbol": row.get("symbol"),
            "strategy": strategy_names.get(str(row.get("strategy_family") or ""), "Неизвестный алгоритм"),
            "timeframe": row.get("timeframe"),
            "stage": stage_names.get(str(row.get("stage_code") or "OOS"), "Неизвестный этап"),
            "future_bars": int(row.get("future_bars") or 0),
            "required_bars": int(row.get("minimum_future_bars") or 0),
            "progress_pct": min(100,round(100*int(row.get("future_bars") or 0)/max(1,int(row.get("minimum_future_bars") or 0)))),
            "state": str(row.get("status_code") or "—").replace("WAITING_FUTURE_DATA", "Ждёт данных"),
            "position": {"OPEN":"Открыта","FLAT":"Нет позиции","CLOSED":"Закрыта"}.get(str(row.get("position_status") or ""), "Нет позиции"),
            "paper_pnl": float(row.get("paper_net_pnl") or 0),
            "risk": {"ALLOW":"Разрешено","BLOCK":"Заблокировано"}.get(str(row.get("risk_decision") or ""), "Нет решения"),
        }
        for row in view_model.swing_summary.get("items", ())
    )


def render_control_center_domain_v2(
    view_model: ControlCenterV2ViewModel,
    *,
    locale_code: str = "ru-RU",
    fallback_locale_code: str = "ru-RU",
    timezone_code: str = "Europe/Moscow",
    generated_at: datetime | None = None,
) -> RenderDocumentV2:
    now = _utc(generated_at) or datetime.now(timezone.utc)
    raw_sections: tuple[tuple[str, tuple[dict[str, Any], ...]], ...] = (
        ("swing_lifecycle", _swing_rows(view_model)),
        ("edge_search_process", tuple(view_model.edge_search_process)),
        ("edge_search_results", tuple(view_model.edge_search_results)),
        ("forward_pass_process", tuple(view_model.forward_pass_process)),
        ("forward_readiness", tuple(view_model.forward_readiness)),
        ("shadow_process", tuple(view_model.shadow_process)),
        ("shadow_alerts", tuple(view_model.shadow_alerts)),
        ("forward_blockers", tuple(view_model.forward_blockers)),
        ("shadow", (dict(view_model.shadow_summary),)),
        ("funnel", _funnel_rows(view_model)),
        ("loss_reasons", _loss_rows(view_model)),
        ("volatility", tuple(view_model.volatility_analysis)),
        ("risk", tuple(view_model.risk_analysis)),
        ("entry", tuple(view_model.entry_analysis)),
        ("execution", tuple(view_model.execution_quality)),
        ("microstructure_priorities", tuple(view_model.microstructure_priorities)),
        ("execution_microstructure", tuple(
            row for row in view_model.execution_variants
            if row.get("cohort_code") == "MICROSTRUCTURE_ONLY"
        )),
        ("execution_historical", tuple(
            row for row in view_model.execution_variants
            if row.get("cohort_code") == "HISTORICAL_BAR_ONLY"
        )),
        ("market", tuple(view_model.market_prerequisites)),
        ("exit", tuple(view_model.exit_analysis)),
        ("block", tuple(view_model.block_analysis)),
        ("shadow_requirements", tuple(view_model.shadow_requirements)),
        ("relationships", _relationship_rows(view_model)),
    )
    source_times = [
        timestamp
        for _, rows in raw_sections
        if (timestamp := _source_as_of(rows)) is not None
    ]
    source_as_of = min(source_times) if source_times else now

    document = RenderDocumentV2(
        document_id="operator.control_center.v2",
        locale_code=locale_code,
        fallback_locale_code=fallback_locale_code,
        timezone_code=timezone_code,
        generated_at=now,
        source_as_of=source_as_of,
        quality_code="VERIFIED" if source_times else "SOURCE_AS_OF_UNAVAILABLE",
        root=RenderNodeV2(
            RenderNodeTypeV2.WORKSPACE,
            "workspace.control_center",
            children=(
                RenderNodeV2(
                    RenderNodeTypeV2.PAGE,
                    "page.control_center",
                    children=(
                        _content_node(
                            RenderNodeTypeV2.TITLE,
                            "control.workspace.title",
                            message_key="research.control.workspace.title",
                            level_code="PAGE",
                        ),
                        _content_node(
                            RenderNodeTypeV2.HEADER,
                            "control.workspace.subtitle",
                            message_key="research.control.workspace.subtitle",
                        ),
                        _traffic_section(view_model),
                        RenderNodeV2(
                            RenderNodeTypeV2.ACTION,
                            "control.action.edge_search",
                            content=RenderContentV2(message_key="research.action.run_edge_search"),
                            action=RenderActionV2(
                                "research.edge_search.run", ActionKindV2.COMMAND,
                                command_code="RESEARCH.RUN_EDGE_SEARCH",
                                policy_class="RESEARCH_MAINTENANCE", reversible=True,
                                rollback_code="RESEARCH.CANCEL_PENDING_REQUEST",
                                idempotency_key="client.request",
                            ),
                        ),
                        RenderNodeV2(
                            RenderNodeTypeV2.ACTION,"control.action.edge_search_cancel",
                            content=RenderContentV2(message_key="research.action.cancel_edge_search"),
                            action=RenderActionV2("research.edge_search.cancel",ActionKindV2.COMMAND,
                                command_code="RESEARCH.CANCEL_EDGE_SEARCH",policy_class="RESEARCH_MAINTENANCE",
                                requires_approval=True,idempotency_key="client.request"),
                        ),
                        *tuple(_table_section(code, rows) for code, rows in raw_sections),
                    ),
                ),
            ),
        ),
    )
    validate_render_document_v2(document)
    return document
