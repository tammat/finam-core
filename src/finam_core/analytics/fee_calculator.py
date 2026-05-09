# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass

from finam_core.storage.fee_profile_repository import FeeProfileRepository


@dataclass(frozen=True)
class FeeResult:
    broker_fee: float
    exchange_fee: float
    clearing_fee: float
    total_fee: float


class FeeCalculator:
    """Русский комментарий: считает оценочные комиссии сделки."""

    def __init__(self, repository: FeeProfileRepository | None = None) -> None:
        self.repository = repository or FeeProfileRepository()

    def calculate(
        self,
        *,
        symbol: str,
        asset_class: str,
        qty: float,
        price: float,
        side: str,
    ) -> FeeResult:
        profile = self.repository.get_profile(asset_class=asset_class, symbol=symbol) or {}

        turnover = abs(float(qty) * float(price))
        qty_abs = abs(float(qty))

        broker_fee = (
            qty_abs * float(profile.get("broker_fee_per_contract") or 0.0)
            + turnover * float(profile.get("broker_fee_pct") or 0.0)
        )

        exchange_fee = (
            qty_abs * float(profile.get("exchange_fee_per_contract") or 0.0)
            + turnover * float(profile.get("exchange_fee_pct") or 0.0)
        )

        clearing_fee = qty_abs * float(profile.get("clearing_fee_per_contract") or 0.0)

        total = broker_fee + exchange_fee + clearing_fee
        min_fee = float(profile.get("min_fee") or 0.0)
        if min_fee > 0:
            total = max(total, min_fee)

        return FeeResult(
            broker_fee=round(broker_fee, 4),
            exchange_fee=round(exchange_fee, 4),
            clearing_fee=round(clearing_fee, 4),
            total_fee=round(total, 4),
        )
