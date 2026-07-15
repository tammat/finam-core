from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Any, Mapping

from marketcore.presentation.render_tree.v2.model import (
    RenderActionV2,
    RenderContentV2,
    RenderDocumentV2,
    RenderNodeStateV2,
    RenderNodeV2,
)
from marketcore.presentation.render_tree.v2.validation import validate_render_document_v2


def _value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, Mapping):
        return {str(key): _value(item) for key, item in sorted(value.items())}
    if isinstance(value, tuple):
        return [_value(item) for item in value]
    if isinstance(value, list):
        return [_value(item) for item in value]
    return value


def _content(content: RenderContentV2) -> dict[str, Any]:
    fields = {
        "message_key": content.message_key,
        "message_args": dict(content.message_args or {}),
        "value": content.value,
        "format_code": content.format_code,
        "level_code": content.level_code,
        "column_code": content.column_code,
    }
    return {key: _value(value) for key, value in fields.items() if value not in (None, {})}


def _state(state: RenderNodeStateV2) -> dict[str, Any]:
    fields = {
        "status_code": state.status_code,
        "quality_code": state.quality_code,
        "availability_code": state.availability_code,
        "freshness_code": state.freshness_code,
        "selected": state.selected,
        "disabled_reason_code": state.disabled_reason_code,
        "source_as_of": state.source_as_of,
        "source_identity": state.source_identity,
    }
    return {key: _value(value) for key, value in fields.items() if value is not None}


def _action(action: RenderActionV2) -> dict[str, Any]:
    fields = {
        "action_id": action.action_id,
        "action_kind": action.action_kind,
        "target_id": action.target_id,
        "command_code": action.command_code,
        "policy_class": action.policy_class,
        "requires_approval": action.requires_approval,
        "reversible": action.reversible,
        "rollback_code": action.rollback_code,
        "expiration": action.expiration,
        "idempotency_key": action.idempotency_key,
        "enabled": action.enabled,
        "blocked_reason_code": action.blocked_reason_code,
    }
    return {key: _value(value) for key, value in fields.items() if value is not None}


def _node(node: RenderNodeV2) -> dict[str, Any]:
    result: dict[str, Any] = {
        "type": node.node_type.value,
        "node_id": node.node_id,
        "children": [_node(child) for child in node.children],
    }
    if node.content is not None:
        result["content"] = _content(node.content)
    if node.state is not None:
        result["state"] = _state(node.state)
    if node.action is not None:
        result["action"] = _action(node.action)
    return result


def render_document_v2_to_dict(document: RenderDocumentV2) -> dict[str, Any]:
    validate_render_document_v2(document)
    return {
        "schema_version": document.schema_version,
        "document_id": document.document_id,
        "locale_code": document.locale_code,
        "fallback_locale_code": document.fallback_locale_code,
        "generated_at": _value(document.generated_at),
        "source_as_of": _value(document.source_as_of),
        "quality_code": document.quality_code,
        "root": _node(document.root),
    }


def render_document_v2_to_json(document: RenderDocumentV2) -> str:
    return json.dumps(
        render_document_v2_to_dict(document),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
