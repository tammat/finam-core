from __future__ import annotations

from html import escape
from typing import Any

from marketcore.presentation.render_tree.render_document import RenderDocument
from marketcore.presentation.render_tree.render_node import RenderNode


class RenderDocumentToHtmlV1:
    """
    Технический адаптер доставки RenderDocument в браузер.

    Не входит в предметную архитектуру RenderTree.
    Единственное место в новом Presentation Layer, которое знает о HTML.
    """

    _TAG_BY_NODE_TYPE = {
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

    @classmethod
    def render(cls, document: RenderDocument) -> str:
        if not isinstance(document, RenderDocument):
            raise TypeError("RENDER_DOCUMENT_REQUIRED")

        return cls._render_node(document.root)

    @classmethod
    def _render_node(cls, node: RenderNode) -> str:
        tag = cls._TAG_BY_NODE_TYPE.get(node.node_type)

        if tag is None:
            raise RuntimeError(
                f"WEB_ADAPTER_UNSUPPORTED_NODE_TYPE:{node.node_type}"
            )

        attributes = cls._render_attributes(node.props)

        content_parts: list[str] = []

        if node.text:
            content_parts.append(escape(str(node.text)))

        content_parts.extend(
            cls._render_node(child)
            for child in node.children
        )

        content = "\n".join(content_parts)

        return f"<{tag}{attributes}>{content}</{tag}>"

    @staticmethod
    def _render_attributes(props: dict[str, Any]) -> str:
        if not props:
            return ""

        attributes: list[str] = []

        for property_name, property_value in props.items():
            if property_value is None:
                continue

            attribute_name = str(property_name).replace("_", "-")

            attributes.append(
                f'{escape(attribute_name)}="{escape(str(property_value))}"'
            )

        if not attributes:
            return ""

        return " " + " ".join(attributes)
