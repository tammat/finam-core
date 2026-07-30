from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PnlUnitSpec:
    symbol: str
    asset_class: str
    price_to_rub_multiplier: float
    currency: str = "RUB"
    source: str = "UNKNOWN"

    def __post_init__(self) -> None:
        if self.currency.upper() != "RUB":
            raise ValueError("PNL_UNIT_NON_RUB_SPEC")
        if self.price_to_rub_multiplier <= 0:
            raise ValueError("PNL_UNIT_INVALID_MULTIPLIER")


def gross_pnl_rub(*, side: str, entry_price: float, exit_price: float,
                  qty: float, spec: PnlUnitSpec) -> float:
    direction = 1.0 if str(side).upper() in {"LONG", "BUY"} else -1.0
    return direction * (float(exit_price) - float(entry_price)) * abs(float(qty)) * spec.price_to_rub_multiplier


def risk_rub(*, entry_price: float, stop_price: float, qty: float,
             spec: PnlUnitSpec) -> float:
    return abs(float(entry_price) - float(stop_price)) * abs(float(qty)) * spec.price_to_rub_multiplier
