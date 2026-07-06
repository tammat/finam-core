from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ContractSpecDTO:
    lot_size: Decimal
    tick_size: Decimal
    tick_value: Decimal
    contract_multiplier: Decimal
    price_precision: int
    min_price: Decimal | None
    max_price: Decimal | None
    source_version: str
