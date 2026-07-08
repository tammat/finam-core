from __future__ import annotations
from marketcore.presentation.components.common.html import h

def render_badge(label: str, tone: str = "neutral") -> str:
    return f'<span class="ui-badge ui-badge-{h(tone)}">{h(label)}</span>'
