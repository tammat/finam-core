from __future__ import annotations

from dataclasses import dataclass
from math import floor


@dataclass(frozen=True)
class RiskPerTradeSize:
    allowed: bool
    qty: int
    risk_rub: float
    risk_per_unit: float
    capital_used: float
    reason: str


class RiskPerTradeSizer:
    """Русский комментарий: рассчитывает объём позиции через риск на сделку."""

    def size(
        self,
        *,
        equity: float,
        risk_pct: float,
        entry_price: float,
        stop_loss: float,
        max_position_value: float,
    ) -> RiskPerTradeSize:
        if equity <= 0:
            return RiskPerTradeSize(False, 0, 0.0, 0.0, 0.0, "equity<=0")

        if risk_pct <= 0:
            return RiskPerTradeSize(False, 0, 0.0, 0.0, 0.0, "risk_pct<=0")

        if entry_price <= 0 or stop_loss <= 0:
            return RiskPerTradeSize(False, 0, 0.0, 0.0, 0.0, "bad_price")

        risk_per_unit = abs(entry_price - stop_loss)

        if risk_per_unit <= 0:
            return RiskPerTradeSize(False, 0, 0.0, 0.0, 0.0, "risk_per_unit<=0")

        max_risk_rub = equity * risk_pct

        qty_by_risk = floor(max_risk_rub / risk_per_unit)
        qty_by_capital = floor(max_position_value / entry_price) if max_position_value > 0 else 0

        qty = min(qty_by_risk, qty_by_capital)

        if qty <= 0:
            return RiskPerTradeSize(
                False,
                0,
                round(max_risk_rub, 2),
                round(risk_per_unit, 4),
                0.0,
                "qty<=0",
            )

        capital_used = qty * entry_price
        actual_risk = qty * risk_per_unit

        return RiskPerTradeSize(
            True,
            qty,
            round(actual_risk, 2),
            round(risk_per_unit, 4),
            round(capital_used, 2),
            (
                f"max_risk={max_risk_rub:.2f};"
                f"qty_by_risk={qty_by_risk};"
                f"qty_by_capital={qty_by_capital};"
                f"qty={qty}"
            ),
        )
