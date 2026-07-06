from __future__ import annotations

from marketcore.presentation.components.html import h


def render_object_card(title: str, fields: dict) -> str:
    rows = "".join(
        f'<div class="object-row"><span>{h(k)}</span><strong>{h(v)}</strong></div>'
        for k, v in fields.items()
    )
    return f'<div class="object-card"><h3>{h(title)}</h3>{rows}</div>'
