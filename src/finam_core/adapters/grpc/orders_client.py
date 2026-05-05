# src/finam_core/adapters/grpc/orders_client.py

from __future__ import annotations

import os
import time
from dataclasses import dataclass


@dataclass
class FinamOrderResult:
    symbol: str
    side: str
    qty: float
    price: float | None
    status: str
    order_id: str | None = None
    reason: str | None = None
    raw: dict | None = None


class FinamOrdersClient:
    """
    Русский комментарий:
    Адаптер реального выставления заявок Finam.
    Стратегия не имеет права использовать этот класс напрямую.
    Вызов только через RealExecutionEngine после RiskEngine.
    """

    def __init__(self) -> None:
        self.account_id = os.getenv("FINAM_ACCOUNT_ID", "").strip()
        self.token = os.getenv("FINAM_TOKEN", "").strip()
        self.endpoint = os.getenv("FINAM_GRPC_ENDPOINT", "api.finam.ru:443").strip()

    def _validate(self, symbol: str, side: str, qty: float) -> str | None:
        if not self.account_id:
            return "FINAM_ACCOUNT_ID_not_set"
        if not self.token:
            return "FINAM_TOKEN_not_set"
        if not symbol:
            return "symbol_not_set"
        if side not in ("BUY", "SELL"):
            return "invalid_side"
        if qty <= 0:
            return "invalid_qty"
        return None

    def place_market_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: float | None = None,
    ) -> FinamOrderResult:
        """
        Русский комментарий:
        Пока безопасная real-заготовка.
        Следующий шаг — заменить PLACEHOLDER на конкретный вызов gRPC Orders API.
        """
        reason = self._validate(symbol, side, qty)
        if reason:
            return FinamOrderResult(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                status="REJECTED",
                reason=reason,
            )

        if os.getenv("REAL_ORDER_CONFIRM", "0") != "1":
            return FinamOrderResult(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                status="REJECTED",
                reason="REAL_ORDER_CONFIRM_not_enabled",
            )

        return FinamOrderResult(
            symbol=symbol,
            side=side,
            qty=qty,
            price=price,
            status="READY_FOR_GRPC_IMPLEMENTATION",
            order_id=f"ready_{symbol}_{side}_{int(time.time() * 1000)}",
            reason="grpc_order_method_not_wired_yet",
            raw={
                "account_id": self.account_id,
                "endpoint": self.endpoint,
                "symbol": symbol,
                "side": side,
                "qty": qty,
                "price": price,
            },
        )
