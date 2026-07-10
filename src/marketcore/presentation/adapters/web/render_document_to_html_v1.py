from __future__ import annotations

from html import escape
from typing import Any

from marketcore.presentation.render_tree.node_types import RenderNodeType
from marketcore.presentation.render_tree.render_document import RenderDocument
from marketcore.presentation.render_tree.render_node import RenderNode


class RenderDocumentToHtmlV1:
    """Внешний адаптер доставки RenderDocument в браузер."""

    _LEGACY_TAG_BY_NODE_TYPE = {
        "main": "main",
        "section": "section",
        "header": "header",
        "article": "article",
        "div": "div",
        "h1": "h1",
        "h2": "h2",
        "h3": "h3",
        "p": "p",
        "a": "a",
        "dl": "dl",
        "dt": "dt",
        "dd": "dd",
    }

    _DOMAIN_TAG_BY_NODE_TYPE = {
        RenderNodeType.WORKSPACE.value: "main",
        RenderNodeType.PAGE.value: "section",
        RenderNodeType.HEADER.value: "header",
        RenderNodeType.SECTION.value: "section",
        RenderNodeType.GRID.value: "div",
        RenderNodeType.CARD.value: "article",
        RenderNodeType.SUBTITLE.value: "p",
        RenderNodeType.TEXT.value: "div",
        RenderNodeType.METRIC_LIST.value: "dl",
        RenderNodeType.METRIC_ROW.value: "div",
        RenderNodeType.METRIC_LABEL.value: "dt",
        RenderNodeType.METRIC_VALUE.value: "dd",
        RenderNodeType.ACTION.value: "a",
        RenderNodeType.BADGE.value: "span",
    }

    @classmethod
    def render(cls, document: RenderDocument) -> str:
        if not isinstance(document, RenderDocument):
            raise TypeError("RENDER_DOCUMENT_REQUIRED")

        return cls._render_node(document.root)

    @classmethod
    def _render_node(cls, node: RenderNode) -> str:
        tag = cls._resolve_tag(node)
        attributes = cls._render_attributes(node.props)

        content_parts: list[str] = []

        if node.text:
            content_parts.append(escape(node.text))

        content_parts.extend(
            cls._render_node(child)
            for child in node.children
        )

        content = "\n".join(content_parts)

        return f"<{tag}{attributes}>{content}</{tag}>"

    @classmethod
    def _resolve_tag(cls, node: RenderNode) -> str:
        node_type = node.type_code

        if node_type == RenderNodeType.TITLE.value:
            return cls._title_tag(node.props)

        tag = cls._DOMAIN_TAG_BY_NODE_TYPE.get(node_type)

        if tag is not None:
            return tag

        tag = cls._LEGACY_TAG_BY_NODE_TYPE.get(node_type)

        if tag is not None:
            return tag

        raise RuntimeError(
            f"WEB_ADAPTER_UNSUPPORTED_NODE_TYPE:{node_type}"
        )

    @staticmethod
    def _title_tag(props: dict[str, Any]) -> str:
        raw_level = props.get("level", 2)

        try:
            level = int(raw_level)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"WEB_ADAPTER_TITLE_LEVEL_INVALID:{raw_level}"
            ) from exc

        if level not in (1, 2, 3):
            raise ValueError(
                f"WEB_ADAPTER_TITLE_LEVEL_UNSUPPORTED:{level}"
            )

        return f"h{level}"

    @staticmethod
    def _render_attributes(props: dict[str, Any]) -> str:
        if not props:
            return ""

        attributes: list[str] = []

        for property_name, property_value in props.items():
            if property_value is None:
                continue

            # level управляет выбором HTML-заголовка и не является атрибутом.
            if property_name == "level":
                continue

            attribute_name = str(property_name).replace("_", "-")

            attributes.append(
                f'{escape(attribute_name)}="{escape(str(property_value))}"'
            )

        if not attributes:
            return ""

        return " " + " ".join(attributes)
