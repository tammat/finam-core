from __future__ import annotations

from html import escape

from marketcore.presentation.design_system.foundation.tokens import STATUS_COLORS
from marketcore.presentation.design_system.registry import DesignComponent, design_registry


def normalize_status(status: str) -> str:
    value = status.upper()
    return value if value in STATUS_COLORS else "INFO"


def Badge(label: str, status: str = "INFO") -> str:
    normalized = normalize_status(status)
    color = STATUS_COLORS[normalized]
    return (
        f'<span class="fc-badge" style="'
        f'background:{color};color:white;border-radius:999px;'
        f'padding:3px 8px;font-size:12px;">'
        f'{escape(label)}</span>'
    )


design_registry.register(DesignComponent("Badge", "components"))
