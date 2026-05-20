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

        print(f"FINAM_ORDER_RAW_RESULT type={type(result)} result={result}", flush=True)

        broker_order_id = None

        if isinstance(result, dict):
            status = str(result.get("status") or "").upper()
            reason = str(result.get("reason") or "")

            broker_order_id = (
                result.get("order_id")
                or result.get("broker_order_id")
                or result.get("transaction_id")
            )

            if status in {"REJECTED", "FAILED", "ERROR"}:
                return FinamOrderResult(
                    ok=False,
                    broker_order_id=None,
                    reason=reason or status,
                )
        else:
            broker_order_id = str(result) if result is not None else None

        return FinamOrderResult(
            ok=bool(broker_order_id),
            broker_order_id=broker_order_id,
            reason="order_sent" if broker_order_id else "empty_order_id",
        )

    def place_sell_limit(
        self,
        *,
        symbol: str,
        qty: float,
        price: float,
    ) -> FinamOrderResult:
        """Русский комментарий: отправляет лимитную SELL-заявку через существующий Finam client."""
        if qty <= 0:
            return FinamOrderResult(False, None, "qty<=0")

        if price <= 0:
            return FinamOrderResult(False, None, "price<=0")

        if hasattr(self.client, "place_limit_order"):
            result = self.client.place_limit_order(
                symbol=symbol,
                side="SELL",
                qty=qty,
                limit_price=price,
            )
        elif hasattr(self.client, "place_order"):
            result = self.client.place_order(
                symbol=symbol,
                side="SELL",
                quantity=qty,
                price=price,
                order_type="LIMIT",
            )
        else:
            return FinamOrderResult(False, None, "client_has_no_order_method")

        print(f"FINAM_ORDER_RAW_RESULT type={type(result)} result={result}", flush=True)

        broker_order_id = None

        if isinstance(result, dict):
            status = str(result.get("status") or "").upper()
            reason = str(result.get("reason") or "")

            broker_order_id = (
                result.get("order_id")
                or result.get("broker_order_id")
                or result.get("transaction_id")
            )

            if status in {"REJECTED", "FAILED", "ERROR"}:
                return FinamOrderResult(
                    ok=False,
                    broker_order_id=None,
                    reason=reason or status,
                )
        else:
            broker_order_id = str(result) if result is not None else None

        return FinamOrderResult(
            ok=bool(broker_order_id),
            broker_order_id=broker_order_id,
            reason="order_sent" if broker_order_id else "empty_order_id",
        )

    def place_buy_market(
        self,
        *,
        symbol: str,
        qty: float,
    ) -> FinamOrderResult:
        """Русский комментарий: отправляет рыночную BUY-заявку через существующий Finam client."""
        if qty <= 0:
            return FinamOrderResult(False, None, "qty<=0")

        if hasattr(self.client, "place_market_order"):
            result = self.client.place_market_order(
                symbol=symbol,
                side="BUY",
                qty=qty,
                price=None,
            )
        elif hasattr(self.client, "place_order"):
            result = self.client.place_order(
                symbol=symbol,
                side="BUY",
                quantity=qty,
                order_type="MARKET",
            )
        else:
            return FinamOrderResult(False, None, "client_has_no_market_order_method")

        print(f"FINAM_MARKET_ORDER_RAW_RESULT type={type(result)} result={result}", flush=True)

        broker_order_id = None

        if isinstance(result, dict):
            status = str(result.get("status") or "").upper()
            reason = str(result.get("reason") or "")

            broker_order_id = (
                result.get("order_id")
                or result.get("broker_order_id")
                or result.get("transaction_id")
            )

            if status in {"REJECTED", "FAILED", "ERROR"}:
                return FinamOrderResult(False, None, reason or status)
        else:
            broker_order_id = str(result) if result is not None else None

        return FinamOrderResult(
            ok=bool(broker_order_id),
            broker_order_id=broker_order_id,
            reason="order_sent" if broker_order_id else "empty_order_id",
        )

