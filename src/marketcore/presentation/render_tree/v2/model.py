from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


SCHEMA_VERSION_V2 = "marketcore.render_tree.v2"


class RenderNodeTypeV2(str, Enum):
    WORKSPACE = "workspace"
    PAGE = "page"
    HEADER = "header"
    SECTION = "section"
    GRID = "grid"
    CARD = "card"
    TABLE = "table"
    TABLE_HEAD = "table_head"
    TABLE_BODY = "table_body"
    TABLE_ROW = "table_row"
    TABLE_HEADER_CELL = "table_header_cell"
    TABLE_CELL = "table_cell"
    TITLE = "title"
    SUBTITLE = "subtitle"
    TEXT = "text"
    METRIC_LIST = "metric_list"
    METRIC_ROW = "metric_row"
    METRIC_LABEL = "metric_label"
    METRIC_VALUE = "metric_value"
    ACTION = "action"
    BADGE = "badge"


class ActionKindV2(str, Enum):
    NAVIGATE = "NAVIGATE"
    QUERY = "QUERY"
    COMMAND = "COMMAND"
    CONFIRM = "CONFIRM"


def _immutable_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


@dataclass(frozen=True, slots=True)
class RenderContentV2:
    message_key: str | None = None
    message_args: Mapping[str, Any] | None = None
    value: Any = None
    format_code: str | None = None
    level_code: str | None = None
    column_code: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "message_args", _immutable_mapping(self.message_args))


@dataclass(frozen=True, slots=True)
class RenderNodeStateV2:
    status_code: str | None = None
    quality_code: str | None = None
    availability_code: str | None = None
    freshness_code: str | None = None
    selected: bool | None = None
    disabled_reason_code: str | None = None
    source_as_of: datetime | None = None
    source_identity: str | None = None


@dataclass(frozen=True, slots=True)
class RenderActionV2:
    action_id: str
    action_kind: ActionKindV2
    target_id: str | None = None
    command_code: str | None = None
    policy_class: str | None = None
    requires_approval: bool = False
    reversible: bool = False
    rollback_code: str | None = None
    expiration: datetime | None = None
    idempotency_key: str | None = None
    enabled: bool = True
    blocked_reason_code: str | None = None


@dataclass(frozen=True, slots=True)
class RenderNodeV2:
    node_type: RenderNodeTypeV2
    node_id: str
    content: RenderContentV2 | None = None
    state: RenderNodeStateV2 | None = None
    action: RenderActionV2 | None = None
    children: tuple["RenderNodeV2", ...] = ()


@dataclass(frozen=True, slots=True)
class RenderDocumentV2:
    document_id: str
    locale_code: str
    fallback_locale_code: str
    generated_at: datetime
    source_as_of: datetime
    quality_code: str
    root: RenderNodeV2
    schema_version: str = SCHEMA_VERSION_V2
