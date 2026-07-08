from __future__ import annotations

from marketcore.presentation.components.common.html import h
from marketcore.presentation.i18n.runtime import tr
from marketcore.presentation.widgets.contracts import WidgetViewModel


def render_widget(vm: WidgetViewModel) -> str:
    rows = []
    for key, value in vm.content.items():
        rows.append(
            '<div class="widget-row">'
            f'<span class="widget-key">{h(key)}</span>'
            f'<span class="widget-value">{h(value)}</span>'
            '</div>'
        )

    return f"""
    <section class="marketcore-widget" data-widget-id="{h(vm.widget_id)}">
        <header class="widget-header">
            <span class="widget-icon">{h(vm.icon)}</span>
            <h2>{tr(vm.title_key)}</h2>
        </header>
        <div class="widget-body">
            {''.join(rows)}
        </div>
        <footer class="widget-footer">
            <span>{h(vm.state)}</span>
            <span>{h(vm.updated_at)}</span>
        </footer>
    </section>
    """


def render_widgets(widgets: list[WidgetViewModel]) -> str:
    ordered = sorted(widgets, key=lambda w: w.priority)
    return f'<div class="marketcore-widget-grid">{"".join(render_widget(w) for w in ordered)}</div>'
