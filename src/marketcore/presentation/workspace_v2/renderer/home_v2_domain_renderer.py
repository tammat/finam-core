from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from marketcore.presentation.framework.base_card import BaseCard
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
from marketcore.presentation.workspace_v2.viewmodel.home_v2_viewmodel import (
    HomeV2ViewModel,
)


_HOME_TARGET_BY_WIDGET_ID = {
    "home.traffic.data": "container.research",
    "home.traffic.edge": "container.edge",
    "home.traffic.forward": "container.edge",
    "home.traffic.execution": "container.risk",
    "home.traffic.live": "container.risk",
    "home.card.profit": "container.capital",
    "home.card.portfolio": "container.portfolio",
    "home.card.portfolio.tablet": "container.portfolio",
    "home.card.portfolio.phone": "container.portfolio",
    "home.card.probe": "container.intraday",
    "home.card.research": "container.research",
    "home.card.control_center": "container.edge",
}


def _utc(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _content_node(
    node_type: RenderNodeTypeV2,
    node_id: str,
    *,
    message_key: str | None = None,
    value: Any = None,
    format_code: str | None = None,
    level_code: str | None = None,
) -> RenderNodeV2:
    return RenderNodeV2(
        node_type=node_type,
        node_id=node_id,
        content=RenderContentV2(
            message_key=message_key,
            value=value,
            format_code=format_code,
            level_code=level_code,
        ),
    )


def _card_state(card: BaseCard) -> RenderNodeStateV2:
    updated_at = _utc(card.payload.get("updated_at"))
    availability = card.payload.get("availability")
    quality = card.payload.get("quality")
    return RenderNodeStateV2(
        status_code=card.status_code.value,
        quality_code=str(quality) if quality else None,
        availability_code=str(availability) if availability else None,
        freshness_code="AS_OF_REPORTED" if updated_at else "AS_OF_UNAVAILABLE",
        source_as_of=updated_at,
        source_identity=(f"home.presenter.{card.widget_id}" if updated_at else None),
    )


def _card_action(card: BaseCard) -> RenderActionV2 | None:
    if not card.actions:
        return None
    target_id = _HOME_TARGET_BY_WIDGET_ID.get(card.widget_id)
    if target_id is None:
        return None
    return RenderActionV2(
        action_id=f"home.navigate.{card.widget_id}",
        action_kind=ActionKindV2.NAVIGATE,
        target_id=target_id,
        enabled=True,
    )


def _card_node(card: BaseCard) -> RenderNodeV2:
    children: list[RenderNodeV2] = [
        _content_node(
            RenderNodeTypeV2.TITLE,
            f"{card.widget_id}.title",
            message_key=card.title_key,
            level_code="CARD",
        )
    ]

    if card.subtitle_key:
        children.append(
            _content_node(
                RenderNodeTypeV2.SUBTITLE,
                f"{card.widget_id}.subtitle",
                message_key=card.subtitle_key,
            )
        )

    primary_value = card.payload.get("primary_value")
    if primary_value is not None:
        children.append(
            _content_node(
                RenderNodeTypeV2.METRIC_VALUE,
                f"{card.widget_id}.primary_value",
                value=primary_value,
                format_code="PRESENTER_VALUE",
            )
        )

    rows_total = card.payload.get("rows_total")
    if rows_total is not None:
        children.append(
            RenderNodeV2(
                RenderNodeTypeV2.METRIC_ROW,
                f"{card.widget_id}.rows",
                children=(
                    _content_node(
                        RenderNodeTypeV2.METRIC_LABEL,
                        f"{card.widget_id}.rows.label",
                        message_key="home.card.status.rows",
                    ),
                    _content_node(
                        RenderNodeTypeV2.METRIC_VALUE,
                        f"{card.widget_id}.rows.value",
                        value=rows_total,
                        format_code="INTEGER",
                    ),
                ),
            )
        )

    updated_at = _utc(card.payload.get("updated_at"))
    if updated_at is not None:
        children.append(
            RenderNodeV2(
                RenderNodeTypeV2.METRIC_ROW,
                f"{card.widget_id}.updated",
                children=(
                    _content_node(
                        RenderNodeTypeV2.METRIC_LABEL,
                        f"{card.widget_id}.updated.label",
                        message_key="home.card.status.updated",
                    ),
                    _content_node(
                        RenderNodeTypeV2.METRIC_VALUE,
                        f"{card.widget_id}.updated.value",
                        value=updated_at,
                        format_code="DATETIME",
                    ),
                ),
            )
        )

    quality = card.payload.get("quality")
    if quality:
        children.append(
            _content_node(
                RenderNodeTypeV2.BADGE,
                f"{card.widget_id}.quality",
                value=str(quality),
                format_code="DOMAIN_CODE",
            )
        )

    return RenderNodeV2(
        node_type=RenderNodeTypeV2.CARD,
        node_id=card.widget_id,
        state=_card_state(card),
        action=_card_action(card),
        children=tuple(children),
    )


def render_home_domain_v2(
    view_model: HomeV2ViewModel,
    *,
    locale_code: str = "ru-RU",
    fallback_locale_code: str = "ru-RU",
    generated_at: datetime | None = None,
) -> RenderDocumentV2:
    now = _utc(generated_at) or datetime.now(timezone.utc)
    layout = view_model.layout
    source_times = [
        source_time
        for section in layout.ordered_sections()
        for card in section.ordered_cards()
        if (source_time := _utc(card.payload.get("updated_at"))) is not None
    ]
    source_as_of = min(source_times) if source_times else now
    quality_code = "VERIFIED" if source_times else "SOURCE_AS_OF_UNAVAILABLE"

    section_nodes: list[RenderNodeV2] = []
    for section in layout.ordered_sections():
        section_nodes.append(
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
                    RenderNodeV2(
                        node_type=RenderNodeTypeV2.GRID,
                        node_id=f"{section.section_id}.grid",
                        children=tuple(_card_node(card) for card in section.ordered_cards()),
                    ),
                ),
            )
        )

    document = RenderDocumentV2(
        document_id="operator.home.v2",
        locale_code=locale_code,
        fallback_locale_code=fallback_locale_code,
        generated_at=now,
        source_as_of=source_as_of,
        quality_code=quality_code,
        root=RenderNodeV2(
            node_type=RenderNodeTypeV2.WORKSPACE,
            node_id="workspace.home",
            children=(
                RenderNodeV2(
                    node_type=RenderNodeTypeV2.PAGE,
                    node_id=layout.layout_id,
                    state=RenderNodeStateV2(status_code=layout.status_code.value),
                    children=(
                        _content_node(
                            RenderNodeTypeV2.TITLE,
                            "home.workspace.title",
                            message_key=layout.title_key,
                            level_code="PAGE",
                        ),
                        _content_node(
                            RenderNodeTypeV2.HEADER,
                            "home.workspace.subtitle",
                            message_key=layout.subtitle_key,
                        ),
                        *section_nodes,
                    ),
                ),
            ),
        ),
    )
    validate_render_document_v2(document)
    return document
