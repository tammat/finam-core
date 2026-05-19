from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FinamOrderResult:
    ok: bool
    broker_order_id: str | None
    reason: str


class FinamOrderClientAdapter:
    """Русский комментарий: тонкий адаптер реальной BUY-заявки через существующий Finam client."""

    def __init__(self, client: Any):
        self.client = client

    def place_buy_limit(
        self,
        *,
        symbol: str,
        qty: float,
        price: float,
    ) -> FinamOrderResult:
        if qty <= 0:
            return FinamOrderResult(False, None, "qty<=0")

        if price <= 0:
            return FinamOrderResult(False, None, "price<=0")

        if hasattr(self.client, "place_limit_order"):
            result = self.client.place_limit_order(
                symbol=symbol,
                side="BUY",
                qty=qty,
                limit_price=price,
            )
        elif hasattr(self.client, "place_order"):
            result = self.client.place_order(
                symbol=symbol,
                side="BUY",
                quantity=qty,
                price=price,
                order_type="LIMIT",
            )
        else:
            return FinamOrderResult(False, None, "client_has_no_order_method")

        broker_order_id = None

        if isinstance(result, dict):
            broker_order_id = (
                result.get("order_id")
                or result.get("broker_order_id")
                or result.get("transaction_id")
            )
        else:
            broker_order_id = str(result) if result is not None else None

        return FinamOrderResult(
            ok=bool(broker_order_id),
            broker_order_id=broker_order_id,
            reason="order_sent" if broker_order_id else "empty_order_id",
        )
