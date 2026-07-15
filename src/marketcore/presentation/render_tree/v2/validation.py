from __future__ import annotations

from datetime import datetime, timezone
from typing import AbstractSet
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from marketcore.presentation.render_tree.v2.model import (
    ActionKindV2,
    RenderActionV2,
    RenderContentV2,
    RenderDocumentV2,
    RenderNodeStateV2,
    RenderNodeTypeV2,
    RenderNodeV2,
    SCHEMA_VERSION_V2,
)


class RenderTreeValidationErrorV2(ValueError):
    pass


_CONTENT_NODE_TYPES = frozenset(
    {
        RenderNodeTypeV2.HEADER,
        RenderNodeTypeV2.TABLE_HEADER_CELL,
        RenderNodeTypeV2.TABLE_CELL,
        RenderNodeTypeV2.TITLE,
        RenderNodeTypeV2.SUBTITLE,
        RenderNodeTypeV2.TEXT,
        RenderNodeTypeV2.METRIC_LABEL,
        RenderNodeTypeV2.METRIC_VALUE,
        RenderNodeTypeV2.ACTION,
        RenderNodeTypeV2.BADGE,
    }
)

_ACTION_NODE_TYPES = frozenset(
    {
        RenderNodeTypeV2.CARD,
        RenderNodeTypeV2.TABLE_ROW,
        RenderNodeTypeV2.ACTION,
    }
)

_FORMAT_CODES = frozenset(
    {
        "BOOLEAN",
        "DATETIME",
        "DECIMAL",
        "DOMAIN_CODE",
        "DOMAIN_VALUE",
        "DURATION_HM",
        "INTEGER",
        "MONEY_RUB",
        "PERCENT",
        "PERCENT_RATIO",
        "PRESENTER_VALUE",
    }
)


def _fail(code: str, detail: str | None = None) -> None:
    raise RenderTreeValidationErrorV2(code if detail is None else f"{code}:{detail}")


def _require_code(value: object, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(code)
    return value


def _validate_utc(value: datetime, code: str) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None:
        _fail(code)
    if value.utcoffset() != timezone.utc.utcoffset(value):
        _fail(code)


def _validate_timezone_code(value: object) -> None:
    timezone_code = _require_code(value, "RENDER_TREE_V2_TIMEZONE_INVALID")
    try:
        ZoneInfo(timezone_code)
    except ZoneInfoNotFoundError:
        _fail("RENDER_TREE_V2_TIMEZONE_UNSUPPORTED", timezone_code)


def _validate_content(
    content: RenderContentV2,
    *,
    node_type: RenderNodeTypeV2,
    message_keys: AbstractSet[str] | None,
) -> None:
    if node_type not in _CONTENT_NODE_TYPES:
        _fail("RENDER_TREE_V2_CONTENT_NOT_ALLOWED", node_type.value)

    if content.message_key is None and content.value is None:
        _fail("RENDER_TREE_V2_CONTENT_EMPTY")

    if content.message_key is not None:
        _require_code(content.message_key, "RENDER_TREE_V2_MESSAGE_KEY_INVALID")
        if message_keys is not None and content.message_key not in message_keys:
            _fail("RENDER_TREE_V2_MESSAGE_KEY_MISSING", content.message_key)

    if content.message_args and content.message_key is None:
        _fail("RENDER_TREE_V2_MESSAGE_ARGS_WITHOUT_KEY")

    if content.format_code is not None:
        format_code = _require_code(content.format_code, "RENDER_TREE_V2_FORMAT_CODE_INVALID")
        if format_code not in _FORMAT_CODES:
            _fail("RENDER_TREE_V2_FORMAT_CODE_UNSUPPORTED", format_code)

    if content.level_code is not None:
        _require_code(content.level_code, "RENDER_TREE_V2_LEVEL_CODE_INVALID")

    if content.column_code is not None:
        _require_code(content.column_code, "RENDER_TREE_V2_COLUMN_CODE_INVALID")

    if isinstance(content.value, str) and ("<" in content.value or ">" in content.value):
        _fail("RENDER_TREE_V2_MARKUP_VALUE_FORBIDDEN")


def _validate_action(action: RenderActionV2, node_type: RenderNodeTypeV2) -> None:
    if node_type not in _ACTION_NODE_TYPES:
        _fail("RENDER_TREE_V2_ACTION_NOT_ALLOWED", node_type.value)

    _require_code(action.action_id, "RENDER_TREE_V2_ACTION_ID_INVALID")

    if not isinstance(action.action_kind, ActionKindV2):
        _fail("RENDER_TREE_V2_ACTION_KIND_INVALID")

    if action.action_kind is ActionKindV2.NAVIGATE:
        _require_code(action.target_id, "RENDER_TREE_V2_NAVIGATION_TARGET_REQUIRED")
        if action.command_code is not None:
            _fail("RENDER_TREE_V2_NAVIGATION_COMMAND_FORBIDDEN")
    else:
        _require_code(action.command_code, "RENDER_TREE_V2_COMMAND_CODE_REQUIRED")

    if action.action_kind in {ActionKindV2.COMMAND, ActionKindV2.CONFIRM}:
        _require_code(action.policy_class, "RENDER_TREE_V2_POLICY_CLASS_REQUIRED")
        _require_code(action.idempotency_key, "RENDER_TREE_V2_IDEMPOTENCY_KEY_REQUIRED")
        if not action.reversible and not action.requires_approval:
            _fail("RENDER_TREE_V2_IRREVERSIBLE_APPROVAL_REQUIRED")

    if action.reversible:
        _require_code(action.rollback_code, "RENDER_TREE_V2_ROLLBACK_CODE_REQUIRED")
    elif action.rollback_code is not None:
        _fail("RENDER_TREE_V2_ROLLBACK_WITHOUT_REVERSIBILITY")

    if action.action_kind is ActionKindV2.CONFIRM and not action.requires_approval:
        _fail("RENDER_TREE_V2_CONFIRM_APPROVAL_REQUIRED")

    if not action.enabled and not action.blocked_reason_code:
        _fail("RENDER_TREE_V2_BLOCKED_REASON_REQUIRED")

    if action.expiration is not None:
        _validate_utc(action.expiration, "RENDER_TREE_V2_ACTION_EXPIRATION_NOT_UTC")


def _validate_state(state: RenderNodeStateV2) -> None:
    if state.source_as_of is not None:
        _validate_utc(state.source_as_of, "RENDER_TREE_V2_NODE_SOURCE_AS_OF_NOT_UTC")
        _require_code(state.source_identity, "RENDER_TREE_V2_NODE_SOURCE_IDENTITY_REQUIRED")
    elif state.source_identity is not None:
        _fail("RENDER_TREE_V2_NODE_SOURCE_AS_OF_REQUIRED")


def validate_render_document_v2(
    document: RenderDocumentV2,
    *,
    message_keys: AbstractSet[str] | None = None,
    maximum_tree_depth: int = 32,
    maximum_nodes: int = 10_000,
) -> None:
    if not isinstance(document, RenderDocumentV2):
        _fail("RENDER_TREE_V2_DOCUMENT_REQUIRED")

    if document.schema_version != SCHEMA_VERSION_V2:
        _fail("RENDER_TREE_V2_SCHEMA_VERSION_UNSUPPORTED", document.schema_version)

    _require_code(document.document_id, "RENDER_TREE_V2_DOCUMENT_ID_INVALID")
    _require_code(document.locale_code, "RENDER_TREE_V2_LOCALE_INVALID")
    _require_code(document.fallback_locale_code, "RENDER_TREE_V2_FALLBACK_LOCALE_INVALID")
    _validate_timezone_code(document.timezone_code)
    _require_code(document.quality_code, "RENDER_TREE_V2_QUALITY_CODE_INVALID")
    _validate_utc(document.generated_at, "RENDER_TREE_V2_GENERATED_AT_NOT_UTC")
    _validate_utc(document.source_as_of, "RENDER_TREE_V2_SOURCE_AS_OF_NOT_UTC")

    if document.source_as_of > document.generated_at:
        _fail("RENDER_TREE_V2_SOURCE_AFTER_GENERATION")

    if document.root.node_type is not RenderNodeTypeV2.WORKSPACE:
        _fail("RENDER_TREE_V2_ROOT_TYPE_INVALID")

    seen_ids: set[str] = set()
    node_count = 0

    def visit(node: RenderNodeV2, depth: int) -> None:
        nonlocal node_count

        if not isinstance(node, RenderNodeV2):
            _fail("RENDER_TREE_V2_NODE_REQUIRED")
        if not isinstance(node.node_type, RenderNodeTypeV2):
            _fail("RENDER_TREE_V2_NODE_TYPE_INVALID")
        if depth > maximum_tree_depth:
            _fail("RENDER_TREE_V2_MAXIMUM_DEPTH_EXCEEDED")

        node_count += 1
        if node_count > maximum_nodes:
            _fail("RENDER_TREE_V2_MAXIMUM_NODES_EXCEEDED")

        node_id = _require_code(node.node_id, "RENDER_TREE_V2_NODE_ID_INVALID")
        if node_id in seen_ids:
            _fail("RENDER_TREE_V2_NODE_ID_DUPLICATE", node_id)
        seen_ids.add(node_id)

        if node.content is not None:
            _validate_content(node.content, node_type=node.node_type, message_keys=message_keys)
        if node.state is not None:
            _validate_state(node.state)
        if node.action is not None:
            _validate_action(node.action, node.node_type)

        if not isinstance(node.children, tuple):
            _fail("RENDER_TREE_V2_CHILDREN_MUST_BE_TUPLE")
        for child in node.children:
            visit(child, depth + 1)

    visit(document.root, 1)
