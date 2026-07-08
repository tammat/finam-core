from __future__ import annotations
from marketcore.presentation.components.common.html import h

def render_card(title: str, body: str, class_name: str = "") -> str:
    classes = "card ui-card" + (f" {h(class_name)}" if class_name else "")
    return f'<section class="{classes}"><h2 class="ui-card-title">{h(title)}</h2><div class="ui-card-body">{body}</div></section>'

def render_kpi_card(label: str, value, hint: str = "") -> str:
    return f'<div class="kpi-card ui-kpi-card"><div class="kpi-label">{h(label)}</div><div class="kpi-value">{h(value)}</div><div class="kpi-hint">{h(hint)}</div></div>'
