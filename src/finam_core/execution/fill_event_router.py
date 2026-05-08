from __future__ import annotations

import re
from typing import Any


class FillEventRouter:
    """
    Routes broker/order fill events into trade-management actions.

    Expected TP client_order_id examples:
    - BRM6_TP1
    - NGK6_TP1
    - tp1:BRM6
    """

    def __init__(self, trade_management):
        self.trade_management = trade_management

    def on_fill(self, event: dict[str, Any]):
        symbol = (
            event.get("symbol")
            or event.get("ticker")
            or event.get("instrument")
        )

        client_order_id = (
            event.get("client_order_id")
            or event.get("order_id")
            or event.get("fill_id")
            or ""
        )

        payload = event.get("payload") or {}
        if isinstance(payload, dict):
            client_order_id = client_order_id or payload.get("client_order_id", "")

        tp_index = self._detect_tp_index(client_order_id, payload)

        if not symbol or tp_index is None:
            return None

        qty = event.get("qty") or event.get("quantity")
        side = self._protective_side(event)

        return self.trade_management.on_take_profit_fill(
            symbol=symbol,
            tp_index=tp_index,
            qty=qty,
            side=side,
            stop_order_id=event.get("stop_order_id"),
        )

    @staticmethod
    def _detect_tp_index(client_order_id: str, payload: dict[str, Any]) -> int | None:
        explicit = payload.get("tp_index") if isinstance(payload, dict) else None
        if explicit is not None:
            try:
                return int(explicit)
            except Exception:
                pass

        s = str(client_order_id).upper()

        m = re.search(r"TP[_\-:]?(\d+)", s)
        if m:
            return int(m.group(1))

        return None

    @staticmethod
    def _protective_side(event: dict[str, Any]) -> str | None:
        """
        If TP fill was SELL, remaining protective stop for long is SELL.
        If TP fill was BUY, remaining protective stop for short is BUY.
        """
        side = event.get("side")
        if side:
            return str(side).upper()
        return None
