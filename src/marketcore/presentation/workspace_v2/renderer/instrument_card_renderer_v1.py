from __future__ import annotations

from html import escape

from marketcore.presentation.workspace_v2.viewmodel.instrument_viewmodel_v1 import (
    InstrumentCardViewModelV1,
)


def render_instrument_card_v1(vm: InstrumentCardViewModelV1) -> str:
    status_class = "mc-v2-badge-warning" if vm.fallback_used else "mc-v2-badge-ok"

    return (
        '<section class="mc-v2-card">'
        f'<div class="mc-v2-kpi-label">{escape(vm.icon)} {escape(vm.badge)}</div>'
        f'<h3>{escape(vm.title)}</h3>'
        f'<div class="mc-v2-kpi-label">{escape(vm.subtitle)}</div>'
        f'<span class="mc-v2-badge {status_class}">{escape(vm.status)}</span>'
        f'<p>{escape(vm.tooltip)}</p>'
        f'<a class="mc-v2-button" href="{escape(vm.navigation_target)}">Открыть</a>'
        '</section>'
    )
