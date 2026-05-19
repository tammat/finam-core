from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RealSellDecision:
    allowed: bool
    reason: str


class RealSellExecutionAdapter:
    """Русский комментарий: защитный SELL-only adapter для выхода из существующего long."""

    def validate(
        self,
        *,
        symbol: str,
        side: str,
        qty: float,
        available_qty: float,
        max_qty: float,
        planned_price: float,
        kill_switch: bool,
    ) -> RealSellDecision:
        if kill_switch:
            return RealSellDecision(False, "kill_switch_active")

        if side.upper() != "SELL":
            return RealSellDecision(False, "only_sell_allowed")

        if symbol != "SBER@MISX":
            return RealSellDecision(False, "only_sber_allowed_v1")

        if qty <= 0:
            return RealSellDecision(False, "qty<=0")

        if qty > max_qty:
            return RealSellDecision(False, f"qty>{max_qty}")

        if available_qty <= 0:
            return RealSellDecision(False, "no_long_position")

        if qty > available_qty:
            return RealSellDecision(False, f"qty>{available_qty}_available")

        if planned_price <= 0:
            return RealSellDecision(False, "planned_price<=0")

        return RealSellDecision(True, "real_sell_allowed")
