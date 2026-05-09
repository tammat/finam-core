# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass

from finam_core.storage.margin_requirement_repository import MarginRequirementRepository


@dataclass(frozen=True)
class MarginResult:
    symbol: str
    qty: float
    initial_margin: float
    maintenance_margin: float
    required_initial_margin: float
    required_maintenance_margin: float
    currency: str


class MarginCalculator:
    """Русский комментарий: считает требуемое ГО по позиции."""

    def __init__(self, repository: MarginRequirementRepository | None = None) -> None:
        self.repository = repository or MarginRequirementRepository()

    def calculate(self, *, symbol: str, qty: float) -> MarginResult:
        row = self.repository.get_by_symbol(symbol) or {}

        initial = float(row.get("initial_margin") or 0.0)
        maintenance = float(row.get("maintenance_margin") or initial)
        qty_abs = abs(float(qty))

        return MarginResult(
            symbol=str(symbol).upper(),
            qty=float(qty),
            initial_margin=round(initial, 4),
            maintenance_margin=round(maintenance, 4),
            required_initial_margin=round(initial * qty_abs, 4),
            required_maintenance_margin=round(maintenance * qty_abs, 4),
            currency=str(row.get("currency") or "RUB"),
        )
