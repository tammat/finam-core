from __future__ import annotations

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

        icon = {
            "STOCK": "📈",
            "SHARE": "📈",
            "FUTURES": "📊",
            "FUTURE": "📊",
            "FX": "💱",
            "CURRENCY": "💱",
            "BOND": "📄",
            "ETF": "🧺",
        }.get(instrument.asset_class.upper(), "◼")

        status = "fallback" if instrument.fallback_used else "ok"

        return InstrumentCardViewModelV1(
            title=instrument.display_name,
            subtitle=instrument.symbol,
            badge=instrument.asset_class,
            status=status,
            icon=icon,
            tooltip=f"{instrument.display_name} / {instrument.exchange} / {instrument.currency}",
            navigation_target=f"/workspace-v2/instruments/{instrument.symbol}",
            source_table=instrument.source_table,
            fallback_used=instrument.fallback_used,
        )
