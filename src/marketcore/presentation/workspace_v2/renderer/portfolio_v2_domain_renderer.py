from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from numbers import Number
from typing import Any

from marketcore.presentation.framework.base_card import BaseCard
from marketcore.presentation.render_tree.v2 import (
    RenderContentV2,
    RenderDocumentV2,
    RenderNodeStateV2,
    RenderNodeTypeV2,
    RenderNodeV2,
    validate_render_document_v2,
)
from marketcore.presentation.workspace_v2.viewmodel.portfolio_v2_viewmodel import (
    PortfolioV2ViewModel,
)


_MONEY_MARKERS = (
    "price",
    "cost",
    "amount",
    "p&l",
    "pnl",
    "profit",
    "loss",
    "equity",
    "cash",
    "цена",
    "стоимость",
    "сумма",
    "прибыль",
    "убыток",
    "результат",
    "оценка",
)

_PERCENT_MARKERS = (
    "_pct",
    "pct",
    "percent",
    "yield",
    "change",
    "процент",
    "доля",
    "%",
)

_DATETIME_MARKERS = ("time", "date", "updated", "created", "время", "дата")


def _utc(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _format_code(column_code: str, value: Any) -> str:
    normalized = column_code.lower()
    if isinstance(value, datetime) or any(marker in normalized for marker in _DATETIME_MARKERS):
        return "DATETIME"
    if any(marker in normalized for marker in _PERCENT_MARKERS):
        return "PERCENT"
    if any(marker in normalized for marker in _MONEY_MARKERS):
        return "MONEY_RUB"
    if isinstance(value, bool):
        return "BOOLEAN"
    if isinstance(value, int):
        return "INTEGER"
    if isinstance(value, (float, Decimal, Number)):
        return "DECIMAL"
    return "DOMAIN_VALUE"


def _content_node(
    node_type: RenderNodeTypeV2,
    node_id: str,
    *,
    message_key: str | None = None,
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
            value=value,
            format_code=format_code,
            level_code=level_code,
            column_code=column_code,
        ),
    )


def _ordered_columns(cards: tuple[BaseCard, ...]) -> tuple[str, ...]:
    result: list[str] = []
    for card in cards:
        for column_code in card.payload.get("values", {}):
            normalized = str(column_code)
            if normalized not in result:
                result.append(normalized)
    return tuple(result)


def _column_key(cards: tuple[BaseCard, ...], column_code: str) -> str:
    for card in cards:
        key = card.payload.get("column_keys", {}).get(column_code)
        if key:
            return str(key)
    return f"portfolio.column.{column_code.lower()}"


def _card_source_as_of(card: BaseCard) -> datetime | None:
    values = card.payload.get("values", {})
    candidates = [
        timestamp
        for column_code, value in values.items()
        if any(marker in str(column_code).lower() for marker in _DATETIME_MARKERS)
        if (timestamp := _utc(value)) is not None
    ]
    return max(candidates) if candidates else None


def _table_node(section_id: str, cards: tuple[BaseCard, ...]) -> RenderNodeV2:
    columns = _ordered_columns(cards)
    header_cells = [
        _content_node(
            RenderNodeTypeV2.TABLE_HEADER_CELL,
            f"{section_id}.header.source",
            message_key="column.data_source",
            column_code="source",
        )
    ]
    header_cells.extend(
        _content_node(
            RenderNodeTypeV2.TABLE_HEADER_CELL,
            f"{section_id}.header.{index}",
            message_key=_column_key(cards, column_code),
            column_code=column_code,
        )
        for index, column_code in enumerate(columns, start=1)
    )

    rows: list[RenderNodeV2] = []
    for row_index, card in enumerate(cards, start=1):
        values = card.payload.get("values", {})
        source_as_of = _card_source_as_of(card)
        cells: list[RenderNodeV2] = [
            _content_node(
                RenderNodeTypeV2.TABLE_CELL,
                f"{card.widget_id}.source",
                message_key=card.title_key,
                column_code="source",
            )
        ]
        for column_index, column_code in enumerate(columns, start=1):
            value = values.get(column_code)
            cells.append(
                _content_node(
                    RenderNodeTypeV2.TABLE_CELL,
                    f"{card.widget_id}.cell.{column_index}",
                    value=value if value is not None else "NO_DATA",
                    format_code=_format_code(column_code, value),
                    column_code=column_code,
                )
            )
        rows.append(
            RenderNodeV2(
                node_type=RenderNodeTypeV2.TABLE_ROW,
                node_id=f"{section_id}.row.{row_index}",
                state=RenderNodeStateV2(
                    status_code=card.status_code.value,
                    freshness_code="AS_OF_REPORTED" if source_as_of else "AS_OF_UNAVAILABLE",
                    source_as_of=source_as_of,
                    source_identity=(str(card.payload.get("source_view")) if source_as_of else None),
                ),
                children=tuple(cells),
            )
        )

    return RenderNodeV2(
        node_type=RenderNodeTypeV2.TABLE,
        node_id=f"{section_id}.table",
        children=(
            RenderNodeV2(
                RenderNodeTypeV2.TABLE_HEAD,
                f"{section_id}.table.head",
                children=(
                    RenderNodeV2(
                        RenderNodeTypeV2.TABLE_ROW,
                        f"{section_id}.table.header_row",
                        children=tuple(header_cells),
                    ),
                ),
            ),
            RenderNodeV2(
                RenderNodeTypeV2.TABLE_BODY,
                f"{section_id}.table.body",
                children=tuple(rows),
            ),
        ),
    )


def render_portfolio_domain_v2(
    view_model: PortfolioV2ViewModel,
    *,
    locale_code: str = "ru-RU",
    fallback_locale_code: str = "ru-RU",
    timezone_code: str = "Europe/Moscow",
    generated_at: datetime | None = None,
) -> RenderDocumentV2:
    now = _utc(generated_at) or datetime.now(timezone.utc)
    source_times = [
        source_time
        for section in view_model.sections
        for card in section.ordered_cards()
        if (source_time := _card_source_as_of(card)) is not None
    ]
    source_as_of = min(source_times) if source_times else now
    quality_code = "VERIFIED" if source_times else "SOURCE_AS_OF_UNAVAILABLE"

    section_nodes = tuple(
        RenderNodeV2(
            node_type=RenderNodeTypeV2.SECTION,
            node_id=section.section_id,
            state=RenderNodeStateV2(status_code=section.status_code.value),
            children=(
                _content_node(
                    RenderNodeTypeV2.TITLE,
                    f"{section.section_id}.title",
                    message_key=section.title_key,
                    level_code="SECTION",
                ),
                _content_node(
                    RenderNodeTypeV2.SUBTITLE,
                    f"{section.section_id}.subtitle",
                    message_key=section.subtitle_key,
                ),
                _table_node(section.section_id, section.ordered_cards()),
            ),
        )
        for section in sorted(view_model.sections, key=lambda item: (item.order, item.section_id))
    )

    document = RenderDocumentV2(
        document_id="operator.portfolio.v2",
        locale_code=locale_code,
        fallback_locale_code=fallback_locale_code,
        timezone_code=timezone_code,
        generated_at=now,
        source_as_of=source_as_of,
        quality_code=quality_code,
        root=RenderNodeV2(
            RenderNodeTypeV2.WORKSPACE,
            "workspace.portfolio",
            children=(
                RenderNodeV2(
                    RenderNodeTypeV2.PAGE,
                    "page.portfolio",
                    children=(
                        _content_node(
                            RenderNodeTypeV2.TITLE,
                            "portfolio.workspace.title",
                            message_key=view_model.title_key,
                            level_code="PAGE",
                        ),
                        _content_node(
                            RenderNodeTypeV2.HEADER,
                            "portfolio.workspace.subtitle",
                            message_key=view_model.subtitle_key,
                        ),
                        *section_nodes,
                    ),
                ),
            ),
        ),
    )
    validate_render_document_v2(document)
    return document
