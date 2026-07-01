from __future__ import annotations

from html import escape

from marketcore.presentation.design_system.components.badges import Badge
from marketcore.presentation.design_system.registry import DesignComponent, design_registry


def HeatmapCard(title: str, items: dict[str, str]) -> str:
    rows = "".join(
        f'<div class="fc-kv-row"><span>{escape(name)}</span>{Badge(status, status)}</div>'
        for name, status in items.items()
    )
    return f'<section class="fc-card"><h3>{escape(title)}</h3>{rows}</section>'


design_registry.register(DesignComponent("HeatmapCard", "heatmap"))
