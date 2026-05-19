from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RealBuyDecision:
    allowed: bool
    reason: str


class RealBuyExecutionAdapter:
    """Русский комментарий: защитный BUY-only adapter для real execution."""

    def validate(
        self,
        *,
        symbol: str,
        side: str,
        qty: float,
        max_qty: float,
        max_position_value: float,
        planned_price: float,
        kill_switch: bool,
    ) -> RealBuyDecision:
        if kill_switch:
            return RealBuyDecision(False, "kill_switch_active")

        if side.upper() != "BUY":
            return RealBuyDecision(False, "only_buy_allowed")

        if qty <= 0:
            return RealBuyDecision(False, "qty<=0")

        if qty > max_qty:
            return RealBuyDecision(False, f"qty>{max_qty}")

        if planned_price <= 0:
            return RealBuyDecision(False, "planned_price<=0")

        value = qty * planned_price

        if value > max_position_value:
            return RealBuyDecision(False, f"position_value>{max_position_value}")

        if "@MISX" not in symbol:
            return RealBuyDecision(False, "only_misx_equities_allowed_v1")

        return RealBuyDecision(True, "real_buy_allowed")
