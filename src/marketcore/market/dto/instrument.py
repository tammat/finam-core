from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InstrumentDTO:
    """
    Immutable описание торгового инструмента.

    Не содержит торговых параметров, комиссий,
    налогов и прочих моделей.
    """

    symbol: str
    instrument_name: str

    exchange_code: str
    asset_class: str
    currency_code: str

    isin: str | None
    figi: str | None

    is_active: bool

    source_version: str
