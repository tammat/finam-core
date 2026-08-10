from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


ZERO = Decimal("0")


class AssetClassV1(StrEnum):
    EQUITY = "EQUITY"
    FUTURES = "FUTURES"


@dataclass(frozen=True, slots=True)
class MonetaryContractV1:
    asset_class: AssetClassV1

    lot_size: Decimal = Decimal("1")
    contract_multiplier: Decimal = Decimal("1")

    tick_size: Decimal = ZERO
    tick_value: Decimal = ZERO


def normalize_gross_pnl_rub_v1(
    *,
    price_pnl: Decimal,
    quantity: Decimal,
    contract: MonetaryContractV1,
) -> Decimal:
    if quantity <= ZERO:
        raise ValueError(
            "quantity must be > 0"
        )

    if contract.asset_class == AssetClassV1.EQUITY:
        if contract.lot_size <= ZERO:
            raise ValueError(
                "equity lot_size must be > 0"
            )

        return (
            price_pnl
            * quantity
            * contract.lot_size
        )

    if contract.asset_class == AssetClassV1.FUTURES:
        if contract.tick_size <= ZERO:
            raise ValueError(
                "futures tick_size must be > 0"
            )

        if contract.tick_value <= ZERO:
            raise ValueError(
                "futures tick_value must be > 0"
            )

        return (
            price_pnl
            / contract.tick_size
            * contract.tick_value
            * quantity
        )

    raise ValueError(
        f"unsupported asset_class={contract.asset_class}"
    )
