from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from marketcore.presentation.render_tree.node_types import RenderNodeType


@dataclass(frozen=True, slots=True)
class RenderNode:
    """Узел платформонезависимого дерева представления.

    Временная совместимость со строковыми node_type сохраняется до завершения
    миграции Home и Portfolio на RenderNodeType.
    """

    node_type: RenderNodeType | str
    props: dict[str, Any] = field(default_factory=dict)
    children: tuple["RenderNode", ...] = ()
    text: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.node_type, (RenderNodeType, str)):
            raise TypeError("RENDER_NODE_TYPE_MUST_BE_ENUM_OR_STRING")

        if isinstance(self.node_type, str) and not self.node_type.strip():
            raise ValueError("RENDER_NODE_TYPE_MUST_NOT_BE_EMPTY")

        if not isinstance(self.props, dict):
            raise TypeError("RENDER_NODE_PROPS_MUST_BE_DICT")

        if not isinstance(self.children, tuple):
            raise TypeError("RENDER_NODE_CHILDREN_MUST_BE_TUPLE")

        if any(not isinstance(child, RenderNode) for child in self.children):
            raise TypeError("RENDER_NODE_CHILD_INVALID")

        if not isinstance(self.text, str):
            raise TypeError("RENDER_NODE_TEXT_MUST_BE_STRING")

    @property
    def type_code(self) -> str:
        """Возвращает стабильный строковый код типа узла."""

        if isinstance(self.node_type, RenderNodeType):
            return self.node_type.value

        return self.node_type
