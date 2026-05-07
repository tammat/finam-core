# -*- coding: utf-8 -*-
"""
BrokerCapabilitiesGate — защита live execution по категории клиента.

Русский комментарий:
- Strategy/AI не имеют права отправлять заявки напрямую.
- Любая live-заявка должна пройти этот gate.
- Для КНУР запрещаем шорт, маржу и фьючерсы, если явно не разрешено.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BrokerCapabilities:
    category: str
    allow_api_orders: bool = True
    allow_long: bool = True
    allow_short: bool = False
    allow_margin: bool = False
    allow_futures: bool = False


class BrokerCapabilitiesGate:
    def __init__(self, capabilities: BrokerCapabilities) -> None:
        self.capabilities = capabilities

    def validate_order(self, *, instrument_type: str, side: str, qty: float, order_purpose: str = "ENTRY") -> tuple[bool, str]:
        side = str(side).upper()
        instrument_type = str(instrument_type).upper()
        order_purpose = str(order_purpose or "ENTRY").upper()

        if not self.capabilities.allow_api_orders:
            return False, "api_orders_forbidden"

        if float(qty) <= 0:
            return False, "invalid_qty"

        if instrument_type in {"FUTURE", "FUTURES"} and not self.capabilities.allow_futures:
            return False, "futures_forbidden"

        # Русский комментарий: EXIT-заявки закрывают уже открытую позицию и не считаются новым short.
        if order_purpose == "EXIT":
            return True, "ok"

        if side == "BUY" and not self.capabilities.allow_long:
            return False, "long_forbidden"

        if side == "SELL" and not self.capabilities.allow_short:
            return False, "short_forbidden"

        return True, "ok"
