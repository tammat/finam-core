from __future__ import annotations

from marketcore.presentation.components.html import h


def render_tree_view(tree: dict) -> str:
    def node(value: object) -> str:
        if isinstance(value, dict):
            items = "".join(f"<li><strong>{h(k)}</strong>{node(v)}</li>" for k, v in value.items())
            return f"<ul class='tree-view'>{items}</ul>"
        return f": <span>{h(value)}</span>"

    return node(tree)
