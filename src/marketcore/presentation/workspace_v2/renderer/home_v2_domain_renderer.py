from __future__ import annotations

from datetime import datetime, timezone
import uuid
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
    "home.traffic.forward": "container.intraday",
    "home.traffic.execution": "container.intraday",
    "home.traffic.live": "container.edge",
    "home.profit_factory.decision": "container.capital",
    "home.profit_factory.expected": "container.capital",
    "home.profit_factory.realized": "container.capital",
    "home.profit_factory.gap": "container.capital",
    "home.profit_factory.roi": "container.capital",
    "home.card.system.status": "container.program",
    "home.card.status.system": "container.program",
    "home.card.status.portfolio": "container.portfolio",
    "home.card.status.research": "container.research",
    "home.card.status.probe": "container.intraday",
    "home.card.status.observation": "container.intraday",
    "home.card.status.runtime": "container.intraday",
    "home.card.profit": "container.capital",
    "home.card.portfolio": "container.portfolio",
    "home.card.portfolio.tablet": "container.portfolio",
    "home.card.portfolio.phone": "container.portfolio",
    "home.card.probe": "container.intraday",
    "home.card.research": "container.research",
    "home.card.control_center": "container.edge",
    "home.operator.model_health": "container.program",
    "home.operator.recommendations": "container.research",
    "home.operator.edge_search": "container.research",
    "home.operator.signal_funnel": "container.edge",
    "home.operator.diagnostic_funnels": "container.research",
    "home.operator.main_loss": "container.research",
    "home.operator.loss_solution": "container.research",
    "home.operator.risk": "container.risk",
    "home.operator.events": "container.program",
}


def _utc(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _operator_domain_message_key(value: Any) -> str:
    return f"home.operator.domain.{str(value).strip().lower()}"


def _operator_compact_status_message_key(value: Any) -> str:
    status = str(value or "").strip().upper()
    return {
        "ACKNOWLEDGED": "home.operator.status.accepted",
        "AWAITING_OPERATOR": "home.operator.status.decision",
        "MEASURING": "home.operator.status.measuring",
        "MEASUREMENT_DUE": "home.operator.status.measure_due",
        "IMPROVED": "home.operator.status.improved",
        "NO_EFFECT": "home.operator.status.no_effect",
        "DEGRADED": "home.operator.status.degraded",
        "STALE": "home.operator.status.stale",
        "EXPIRED": "home.operator.status.expired",
        "BLOCKED": "home.operator.status.blocked",
        "MEASURED": "home.operator.status.done",
        "COMPLETED": "home.operator.status.done",
        "PENDING": "home.operator.status.waiting",
        "NEEDS_OPERATOR_DECISION": "home.operator.status.decision",
    }.get(status, "home.operator.status.waiting")


def _content_node(
    node_type: RenderNodeTypeV2,
    node_id: str,
    *,
    message_key: str | None = None,
    message_args: dict[str, Any] | None = None,
    value: Any = None,
    format_code: str | None = None,
    level_code: str | None = None,
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
    decision_id = card.payload.get("operator_decision_id")
    if decision_id and card.payload.get("operator_action_enabled"):
        expiration = _utc(card.payload.get("operator_action_expires_at"))
        action_id = str(card.payload["operator_action_id"])
        return RenderActionV2(
            action_id=action_id,
            action_kind=ActionKindV2.COMMAND,
            target_id=str(decision_id),
            command_code=str(card.payload["operator_command_code"]),
            policy_class="OPERATOR_FEEDBACK",
            reversible=True,
            rollback_code=str(card.payload["operator_rollback_code"]),
            expiration=expiration,
            idempotency_key=str(uuid.uuid5(uuid.NAMESPACE_URL,f"marketcore:{action_id}:{decision_id}:{expiration}")),
        )
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

    v2_message_key = card.payload.get("v2_message_key")
    v2_value = card.payload.get("v2_value")
    v2_format_code = card.payload.get("v2_format_code")
    if v2_message_key:
        children.append(
            _content_node(
                RenderNodeTypeV2.METRIC_VALUE,
                f"{card.widget_id}.primary_value",
                message_key=str(v2_message_key),
                message_args=dict(card.payload.get("v2_message_args") or {}),
            )
        )
    elif v2_value is not None:
        children.append(
            _content_node(
                RenderNodeTypeV2.METRIC_VALUE,
                f"{card.widget_id}.primary_value",
                message_key=(
                    _operator_domain_message_key(v2_value)
                    if card.widget_id.startswith("home.operator.") and v2_format_code == "DOMAIN_CODE"
                    else None
                ),
                value=(
                    None
                    if card.widget_id.startswith("home.operator.") and v2_format_code == "DOMAIN_CODE"
                    else v2_value
                ),
                format_code=(
                    None
                    if card.widget_id.startswith("home.operator.") and v2_format_code == "DOMAIN_CODE"
                    else str(v2_format_code)
                ),
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
                message_key=(
                    _operator_domain_message_key(quality)
                    if card.widget_id.startswith("home.operator.")
                    else None
                ),
                value=None if card.widget_id.startswith("home.operator.") else str(quality),
                format_code=None if card.widget_id.startswith("home.operator.") else "DOMAIN_CODE",
            )
        )

    for field_index, (label_key, field_value, format_code) in enumerate(card.payload.get("operator_fields") or (), start=1):
        children.append(
            RenderNodeV2(
                RenderNodeTypeV2.METRIC_ROW,
                f"{card.widget_id}.operator_field.{field_index}",
                children=(
                    _content_node(RenderNodeTypeV2.METRIC_LABEL,f"{card.widget_id}.operator_field.{field_index}.label",message_key=label_key),
                    _content_node(
                        RenderNodeTypeV2.METRIC_VALUE,
                        f"{card.widget_id}.operator_field.{field_index}.value",
                        message_key=(
                            _operator_domain_message_key("NO_DATA" if field_value is None else field_value)
                            if field_value is None or format_code == "DOMAIN_CODE"
                            else None
                        ),
                        value=None if field_value is None or format_code == "DOMAIN_CODE" else field_value,
                        format_code=None if field_value is None or format_code == "DOMAIN_CODE" else format_code,
                    ),
                ),
            )
        )

    return RenderNodeV2(
        node_type=RenderNodeTypeV2.CARD,
        node_id=card.widget_id,
        state=_card_state(card),
        action=_card_action(card),
        children=tuple(children),
    )


def _operator_action_table(cards: tuple[BaseCard, ...]) -> RenderNodeV2:
    columns = (
        ("priority", "column.operator.number"),
        ("task", "column.operator.task"),
        ("reason", "column.operator.reason"),
        ("effect", "column.operator.effect"),
        ("status", "column.operator.verdict"),
        ("expires", "column.operator.deadline"),
        ("action", "column.operator.action"),
    )
    header = RenderNodeV2(
        RenderNodeTypeV2.TABLE_ROW,
        "home.operator.actions.table.header",
        children=tuple(
            _content_node(
                RenderNodeTypeV2.TABLE_HEADER_CELL,
                f"home.operator.actions.table.header.{code}",
                message_key=message_key,
            )
            for code, message_key in columns
        ),
    )
    rows = []
    for display_number, card in enumerate(cards, start=1):
        fields = {
            label_key: (value, format_code)
            for label_key, value, format_code in card.payload.get("operator_fields") or ()
        }
        action_value = card.payload.get("v2_value")
        loss_value, _ = fields.get("home.operator.field.loss_source", (None, "DOMAIN_CODE"))
        effect_value, _ = fields.get("home.operator.field.expected_profit_impact", (None, "MONEY_RUB"))
        actual_value, actual_format = fields.get("home.operator.field.actual_result", (None, "DECIMAL"))
        verdict_value, _ = fields.get("home.operator.field.policy_verdict", (None, "DOMAIN_CODE"))
        expires_value, _ = fields.get("home.operator.field.expires_at", (None, "DATETIME"))
        measured_value, _ = fields.get("home.operator.field.measured_at", (None, "DATETIME"))
        if card.payload.get("operator_action_enabled"):
            next_key = "home.operator.next.measure" if str(verdict_value) == "MEASUREMENT_DUE" else (
                "home.operator.next.refresh" if str(verdict_value) in {"IMPROVED", "NO_EFFECT", "DEGRADED"} else "home.operator.next.open"
            )
        elif str(verdict_value) == "BLOCKED":
            next_key = "home.operator.next.review_block"
        elif str(verdict_value) == "MEASURING":
            next_key = "home.operator.next.automatic"
        elif str(verdict_value) in {"IMPROVED", "NO_EFFECT", "DEGRADED", "EXPIRED", "STALE"}:
            next_key = "home.operator.next.view"
        else:
            next_key = "home.operator.next.wait"
        displayed_effect = actual_value if actual_value is not None else effect_value
        displayed_effect_format = actual_format if actual_value is not None else "MONEY_RUB"
        values = (
            _content_node(RenderNodeTypeV2.TABLE_CELL,f"{card.widget_id}.priority",value=display_number,format_code="INTEGER"),
            _content_node(RenderNodeTypeV2.TABLE_CELL,f"{card.widget_id}.action",message_key=_operator_domain_message_key(action_value)),
            _content_node(RenderNodeTypeV2.TABLE_CELL,f"{card.widget_id}.reason",message_key=_operator_domain_message_key(loss_value)),
            _content_node(RenderNodeTypeV2.TABLE_CELL,f"{card.widget_id}.effect",message_key=_operator_domain_message_key("NO_DATA") if displayed_effect is None else None,value=displayed_effect,format_code=None if displayed_effect is None else displayed_effect_format),
            _content_node(RenderNodeTypeV2.TABLE_CELL,f"{card.widget_id}.status",message_key=_operator_compact_status_message_key(verdict_value)),
            _content_node(RenderNodeTypeV2.TABLE_CELL,f"{card.widget_id}.expires",value=measured_value or expires_value,format_code="DATETIME"),
            _content_node(RenderNodeTypeV2.TABLE_CELL,f"{card.widget_id}.next",message_key=next_key),
        )
        rows.append(RenderNodeV2(
            RenderNodeTypeV2.TABLE_ROW,
            card.widget_id,
            state=_card_state(card),
            action=_card_action(card),
            children=values,
        ))
    return RenderNodeV2(
        RenderNodeTypeV2.TABLE,
        "home.operator.actions.table",
        children=(
            RenderNodeV2(RenderNodeTypeV2.TABLE_HEAD,"home.operator.actions.table.head",children=(header,)),
            RenderNodeV2(RenderNodeTypeV2.TABLE_BODY,"home.operator.actions.table.body",children=tuple(rows)),
        ),
    )


def render_home_domain_v2(
    view_model: HomeV2ViewModel,
    *,
    locale_code: str = "ru-RU",
    fallback_locale_code: str = "ru-RU",
    timezone_code: str = "Europe/Moscow",
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
        ordered_cards = section.ordered_cards()
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
                        children=tuple(_card_node(card) for card in ordered_cards),
                    ) if section.section_id != "home.operator.actions" else _operator_action_table(ordered_cards),
                ),
            )
        )

    document = RenderDocumentV2(
        document_id="operator.home.v2",
        locale_code=locale_code,
        fallback_locale_code=fallback_locale_code,
        timezone_code=timezone_code,
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
