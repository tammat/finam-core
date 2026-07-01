from __future__ import annotations

from html import escape

from marketcore.presentation.design_system.registry import DesignComponent, design_registry


def DashboardGrid(cards: list[str]) -> str:
    return '<div class="fc-grid">' + "".join(cards) + "</div>"


def SectionHeader(title: str) -> str:
    return f'<h2 class="fc-section-title">{escape(title)}</h2>'


design_registry.register(DesignComponent("DashboardGrid", "layout"))
design_registry.register(DesignComponent("SectionHeader", "layout"))
