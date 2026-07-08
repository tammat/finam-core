from __future__ import annotations
from marketcore.presentation.components.common.html import h

def render_section(title: str, body: str, class_name: str = "") -> str:
    classes = "ui-section" + (f" {h(class_name)}" if class_name else "")
    return f'<section class="{classes}"><h2 class="ui-section-title">{h(title)}</h2><div class="ui-section-body">{body}</div></section>'
