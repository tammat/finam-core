from __future__ import annotations

from html import escape
from typing import Any

from marketcore.presentation.render_tree.render_document import RenderDocument
from marketcore.presentation.render_tree.render_node import RenderNode


class WebRenderer:
    TAGS = {
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
        return cls._node(document.root)

    @classmethod
    def _node(cls, node: RenderNode) -> str:
        tag = cls.TAGS.get(node.node_type)
        if not tag:
            raise RuntimeError(f"UNKNOWN_RENDER_NODE:{node.node_type}")

        attrs = cls._attrs(node.props)
        inner = escape(node.text) if node.text else ""
        if node.children:
            inner += "\n".join(cls._node(child) for child in node.children)

        return f"<{tag}{attrs}>{inner}</{tag}>"

    @staticmethod
    def _attrs(props: dict[str, Any]) -> str:
        if not props:
            return ""

        parts = []
        for key, value in props.items():
            if value is None:
                continue
            attr = key.replace("_", "-")
            parts.append(f'{escape(attr)}="{escape(str(value))}"')

        return " " + " ".join(parts)
