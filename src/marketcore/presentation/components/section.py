from __future__ import annotations

from marketcore.presentation.components.html import h


def render_section(title: str, body: str) -> str:
    return f'<section class="ui-section"><h2>{h(title)}</h2>{body}</section>'
