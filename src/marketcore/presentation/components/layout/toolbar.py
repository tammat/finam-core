from __future__ import annotations

def render_toolbar(items: list[str]) -> str:
    return f'<div class="ui-toolbar">{"".join(items)}</div>'
