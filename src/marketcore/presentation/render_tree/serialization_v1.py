from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Any

from marketcore.presentation.render_tree.render_document import RenderDocument
from marketcore.presentation.render_tree.render_node import RenderNode


class RenderTreeSerializationErrorV1(ValueError):
    """Ошибка сериализации платформонезависимого дерева представления."""


class RenderTreeSerializerV1:
    """Сериализует RenderDocument в словарь или JSON.

    Модуль не содержит зависимостей от конкретной платформы доставки.
    """

    SCHEMA_VERSION = "marketcore.render_tree.v1"

    @classmethod
    def to_dict(cls, document: RenderDocument) -> dict[str, Any]:
        if not isinstance(document, RenderDocument):
            raise TypeError("RENDER_DOCUMENT_REQUIRED")

        return {
            "schema_version": cls.SCHEMA_VERSION,
            "root": cls._node_to_dict(document.root),
        }

    @classmethod
    def to_json(
        cls,
        document: RenderDocument,
        *,
        ensure_ascii: bool = False,
        sort_keys: bool = True,
        indent: int | None = None,
    ) -> str:
        payload = cls.to_dict(document)

        return json.dumps(
            payload,
            ensure_ascii=ensure_ascii,
            sort_keys=sort_keys,
            indent=indent,
            separators=None if indent is not None else (",", ":"),
        )

    @classmethod
    def _node_to_dict(cls, node: RenderNode) -> dict[str, Any]:
        if not isinstance(node, RenderNode):
            raise TypeError("RENDER_NODE_REQUIRED")

        return {
            "type": node.type_code,
            "props": cls._normalize_value(
                node.props,
                path=f"node[{node.type_code}].props",
            ),
            "text": node.text,
            "children": [
                cls._node_to_dict(child)
                for child in node.children
            ],
        }

    @classmethod
    def _normalize_value(
        cls,
        value: Any,
        *,
        path: str,
    ) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value

        if isinstance(value, Enum):
            return cls._normalize_value(
                value.value,
                path=path,
            )

        if isinstance(value, Mapping):
            normalized: dict[str, Any] = {}

            for key, nested_value in value.items():
                if not isinstance(key, str):
                    raise RenderTreeSerializationErrorV1(
                        f"RENDER_TREE_PROP_KEY_MUST_BE_STRING:"
                        f"path={path}:key={key!r}"
                    )

                normalized[key] = cls._normalize_value(
                    nested_value,
                    path=f"{path}.{key}",
                )

            return normalized

        if isinstance(value, tuple):
            return [
                cls._normalize_value(
                    nested_value,
                    path=f"{path}[{index}]",
                )
                for index, nested_value in enumerate(value)
            ]

        if isinstance(value, list):
            return [
                cls._normalize_value(
                    nested_value,
                    path=f"{path}[{index}]",
                )
                for index, nested_value in enumerate(value)
            ]

        if isinstance(value, Sequence) and not isinstance(
            value,
            (str, bytes, bytearray),
        ):
            return [
                cls._normalize_value(
                    nested_value,
                    path=f"{path}[{index}]",
                )
                for index, nested_value in enumerate(value)
            ]

        raise RenderTreeSerializationErrorV1(
            "RENDER_TREE_VALUE_NOT_SERIALIZABLE:"
            f"path={path}:type={type(value).__name__}"
        )
