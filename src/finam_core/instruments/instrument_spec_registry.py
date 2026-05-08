# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass

from finam_core.storage.instrument_spec_repository import InstrumentSpecRepository


@dataclass(frozen=True)
class InstrumentSpec:
    symbol: str
    base_symbol: str
    asset_class: str
    min_price_step: float
    step_value: float
    lot_size: float = 1.0
    currency: str = "RUB"
    broker_fee: float = 0.0
    exchange_fee: float = 0.0
    clearing_fee: float = 0.0
    tax_rate: float = 0.13


class InstrumentSpecRegistry:
    """Русский комментарий: registry спецификаций с PostgreSQL-first и безопасным fallback."""

    FALLBACKS = {
        "BR": InstrumentSpec("BR", "BR", "FUTURES", 0.01, 10.0),
        "SI": InstrumentSpec("SI", "SI", "FUTURES", 1.0, 1.0),
        "NG": InstrumentSpec("NG", "NG", "FUTURES", 0.001, 1.0),
        "RI": InstrumentSpec("RI", "RI", "FUTURES", 10.0, 10.0),
        "MX": InstrumentSpec("MX", "MX", "FUTURES", 0.25, 1.0),
    }

    def __init__(self, repository: InstrumentSpecRepository | None = None) -> None:
        self.repository = repository or InstrumentSpecRepository()

    def get(self, symbol: str) -> InstrumentSpec:
        symbol_u = str(symbol or "").upper()
        base = symbol_u.split("@", 1)[0]

        try:
            row = self.repository.get_by_symbol(symbol_u)
            if row:
                return InstrumentSpec(
                    symbol=str(row["symbol"]),
                    base_symbol=str(row["base_symbol"]),
                    asset_class=str(row["asset_class"]),
                    min_price_step=float(row["min_price_step"] or 1.0),
                    step_value=float(row["step_value"] or 1.0),
                    lot_size=float(row["lot_size"] or 1.0),
                    currency=str(row["currency"] or "RUB"),
                    broker_fee=float(row["broker_fee"] or 0.0),
                    exchange_fee=float(row["exchange_fee"] or 0.0),
                    clearing_fee=float(row["clearing_fee"] or 0.0),
                    tax_rate=float(row["tax_rate"] or 0.13),
                )
        except Exception as exc:
            print(f"INSTRUMENT_SPEC_REGISTRY_DB_FALLBACK symbol={symbol_u} error={exc}", flush=True)

        for prefix, spec in self.FALLBACKS.items():
            if base.startswith(prefix):
                return spec

        return InstrumentSpec(symbol_u, base, "UNKNOWN", 1.0, 1.0)
