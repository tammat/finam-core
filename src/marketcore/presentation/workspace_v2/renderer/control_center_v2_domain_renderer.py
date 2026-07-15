from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import Decimal
from numbers import Number
from typing import Any, Iterable

from marketcore.presentation.render_tree.v2 import (
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


def _utc(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _display_value(column_code: str, value: Any) -> tuple[Any, str]:
    normalized = column_code.lower()
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
            display_value, format_code = _display_value(column, row.get(column))
            cells.append(
                _content_node(
                    RenderNodeTypeV2.TABLE_CELL,
                    f"{section_id}.row.{row_index}.cell.{column_index}",
                    value=display_value,
                    format_code=format_code,
                    column_code=column,
                )
            )
        body_rows.append(
            RenderNodeV2(
                RenderNodeTypeV2.TABLE_ROW,
                f"{section_id}.row.{row_index}",
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
            "family": item.family,
            "source": item.source,
            "target": item.target,
            "regime": item.regime,
            "session": item.session,
            "oos_trades": item.oos_trades,
            "profit_factor": item.profit_factor,
            "expectancy_bps": item.expectancy_bps,
            "coverage_pct": item.coverage_pct,
            "verdict": item.verdict,
            "status": item.status,
        }
        for item in view_model.relationships
    )


def _funnel_rows(view_model: ControlCenterV2ViewModel) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "stage": item.label,
            "count": item.count,
            "conversion": item.conversion,
            "status": item.status,
        }
        for item in view_model.funnel_stages
    )


def _loss_rows(view_model: ControlCenterV2ViewModel) -> tuple[dict[str, Any], ...]:
    return tuple(
        {
            "reason_code": item.code,
            "label": item.label,
            "count": item.count,
            "recommended_action": item.action,
            "status": item.status,
        }
        for item in view_model.loss_reasons
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
        ("shadow", (dict(view_model.shadow_summary),)),
        ("funnel", _funnel_rows(view_model)),
        ("loss_reasons", _loss_rows(view_model)),
        ("volatility", tuple(view_model.volatility_analysis)),
        ("risk", tuple(view_model.risk_analysis)),
        ("entry", tuple(view_model.entry_analysis)),
        ("execution", tuple(view_model.execution_quality)),
        ("execution_variants", tuple(view_model.execution_variants)),
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
                        *tuple(_table_section(code, rows) for code, rows in raw_sections),
                    ),
                ),
            ),
        ),
    )
    validate_render_document_v2(document)
    return document
