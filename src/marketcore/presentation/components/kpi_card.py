from __future__ import annotations

from marketcore.presentation.components.html import h


def render_kpi_card(title: str, value: object, subtitle: str = "") -> str:
    return (
        '<div class="kpi-card">'
        f'<div class="kpi-title">{h(title)}</div>'
        f'<div class="kpi-value">{h(value)}</div>'
        f'<div class="kpi-subtitle">{h(subtitle)}</div>'
        "</div>"
    )
