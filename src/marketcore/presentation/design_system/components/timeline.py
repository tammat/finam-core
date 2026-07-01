from __future__ import annotations

from html import escape

from marketcore.presentation.design_system.registry import DesignComponent, design_registry


def TimelineCard(title: str, events: list[dict[str, str]]) -> str:
    items = "".join(
        f'<li><strong>{escape(e.get("time", ""))}</strong> {escape(e.get("text", ""))}</li>'
        for e in events
    )
    return f'<section class="fc-card"><h3>{escape(title)}</h3><ul>{items}</ul></section>'


design_registry.register(DesignComponent("TimelineCard", "timeline"))
