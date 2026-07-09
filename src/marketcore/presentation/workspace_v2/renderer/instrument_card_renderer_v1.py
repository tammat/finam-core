from __future__ import annotations

from html import escape

from marketcore.presentation.framework.registry import UiStatusCode
from marketcore.presentation.workspace_v2.viewmodel.instrument_viewmodel_v1 import (
    InstrumentCardViewModelV1,
)


def render_instrument_card_v1(vm: InstrumentCardViewModelV1) -> str:
    status_class = (
        "mc-v2-badge-warning"
        if vm.status_code == UiStatusCode.FALLBACK
        else "mc-v2-badge-ok"
    )

    return (
        '<section class="mc-v2-card">'
        f'<div class="mc-v2-kpi-label" data-icon-key="{escape(vm.icon_key)}">{escape(vm.badge_key)}</div>'
        f'<h3 data-i18n-key="{escape(vm.title_key)}"></h3>'
        f'<div class="mc-v2-kpi-label" data-i18n-key="{escape(vm.subtitle_key)}"></div>'
        f'<span class="mc-v2-badge {status_class}">{escape(vm.status_code.value)}</span>'
        f'<p data-i18n-key="{escape(vm.tooltip_key)}"></p>'
        f'<a class="mc-v2-button" href="{escape(vm.navigation_target)}" data-i18n-key="ui.action.open"></a>'
        '</section>'
    )
