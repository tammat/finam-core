from __future__ import annotations

from marketcore.presentation.framework.registry import UiStatusCode
from marketcore.presentation.workspace_v2.resolver.instrument_display_resolver_v1 import (
    InstrumentDisplayResolverV1,
)
from marketcore.presentation.workspace_v2.viewmodel.instrument_viewmodel_v1 import (
    InstrumentCardViewModelV1,
)


class InstrumentPresenterV1:
    def __init__(self) -> None:
        self._resolver = InstrumentDisplayResolverV1()

    def card(self, symbol: str) -> InstrumentCardViewModelV1:
        instrument = self._resolver.resolve(symbol)

        return InstrumentCardViewModelV1(
            title_key=instrument.title_key,
            subtitle_key=instrument.subtitle_key,
            badge_key=instrument.badge_key,
            status_code=UiStatusCode.FALLBACK if instrument.fallback_used else UiStatusCode.OK,
            icon_key=instrument.brand_icon_key,
            tooltip_key=instrument.tooltip_key,
            navigation_target=f"/workspace-v2/instruments/{instrument.symbol}",
            source_table=instrument.source_table,
            fallback_used=instrument.fallback_used,
        )
