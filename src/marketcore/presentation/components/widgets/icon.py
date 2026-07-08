from __future__ import annotations
from marketcore.presentation.components.common.html import h

def render_icon(icon: str, label: str = "") -> str:
    return f'<span class="ui-icon" aria-label="{h(label)}">{h(icon)}</span>'
