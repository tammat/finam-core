from __future__ import annotations
from marketcore.presentation.components.common.html import h
from marketcore.presentation.components.widgets.icon import render_icon

def render_button(label: str, href: str | None = None, icon: str = "", disabled: bool = False) -> str:
    icon_html = render_icon(icon, label) if icon else ""
    label_html = f'<span class="ui-button-label">{h(label)}</span>'
    if disabled:
        return f'<span class="ui-button ui-button-disabled" aria-disabled="true">{icon_html}{label_html}</span>'
    if href:
        return f'<a class="ui-button" href="{h(href)}">{icon_html}{label_html}</a>'
    return f'<button class="ui-button" type="button">{icon_html}{label_html}</button>'
