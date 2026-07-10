from __future__ import annotations

from enum import Enum


class RenderNodeType(str, Enum):
    """Платформонезависимые типы узлов дерева представления."""

    WORKSPACE = "workspace"
    PAGE = "page"
    HEADER = "header"

    SECTION = "section"
    GRID = "grid"
    CARD = "card"

    TITLE = "title"
    SUBTITLE = "subtitle"
    TEXT = "text"

    METRIC_LIST = "metric_list"
    METRIC_ROW = "metric_row"
    METRIC_LABEL = "metric_label"
    METRIC_VALUE = "metric_value"

    ACTION = "action"
    BADGE = "badge"

    def __str__(self) -> str:
        return self.value


DOMAIN_RENDER_NODE_TYPES: frozenset[str] = frozenset(
    node_type.value
    for node_type in RenderNodeType
)


def is_domain_render_node_type(value: object) -> bool:
    """Проверяет принадлежность значения реестру доменных типов."""

    if isinstance(value, RenderNodeType):
        return True

    if not isinstance(value, str):
        return False

    return value in DOMAIN_RENDER_NODE_TYPES
