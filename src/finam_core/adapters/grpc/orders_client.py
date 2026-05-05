# src/finam_core/adapters/grpc/orders_client.py

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import grpc
from google.type import decimal_pb2


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
        self._channel: Any | None = None
        self._stub: Any | None = None

    def _validate(self, symbol: str, side: str, qty: float) -> str | None:
        if not self.account_id:
            return "FINAM_ACCOUNT_ID_not_set"
        if not self.token:
            return "FINAM_TOKEN_not_set"
        if self.token.count(".") != 2:
            return "FINAM_TOKEN_not_jwt"
        if not symbol:
            return "symbol_not_set"
        if side not in ("BUY", "SELL"):
            return "invalid_side"
        if qty <= 0:
            return "invalid_qty"
        return None

    def _metadata(self) -> list[tuple[str, str]]:
        """Русский комментарий: metadata для gRPC-вызова Finam."""
        return [("authorization", f"Bearer {self.token}")]

    def _load_orders_grpc(self):
        """Русский комментарий: лениво загружает protobuf-модули Orders API."""
        try:
            from finam_proto.grpc.tradeapi.v1.orders import orders_service_pb2, orders_service_pb2_grpc  # type: ignore
            from finam_proto.grpc.tradeapi.v1 import side_pb2  # type: ignore
            return orders_service_pb2, orders_service_pb2_grpc, side_pb2
        except Exception as exc:
            raise RuntimeError(f"orders_grpc_modules_not_available: {exc}") from exc

    def _stub_for_orders(self):
        """Русский комментарий: создаёт gRPC stub только при подтверждённом real-вызове."""
        if self._stub is not None:
            return self._stub

        _, orders_service_pb2_grpc, _ = self._load_orders_grpc()
        self._channel = grpc.secure_channel(self.endpoint, grpc.ssl_channel_credentials())
        self._stub = orders_service_pb2_grpc.OrdersServiceStub(self._channel)
        return self._stub

    def _side_value(self, side: str):
        """Русский комментарий: подбирает enum Side по фактическим именам в proto."""
        _, _, side_pb2 = self._load_orders_grpc()
        for name in (side, f"SIDE_{side}", f"ORDER_SIDE_{side}", f"BUY_SELL_{side}"):
            if hasattr(side_pb2, name):
                return getattr(side_pb2, name)
        raise RuntimeError("orders_side_enum_not_found")

    def _build_market_order(self, symbol: str, side: str, qty: float):
        """Русский комментарий: строит Order для OrdersService.PlaceOrder."""
        orders_service_pb2, _, _ = self._load_orders_grpc()
        return orders_service_pb2.Order(
            account_id=self.account_id,
            symbol=symbol,
            quantity=decimal_pb2.Decimal(value=str(int(qty))),
            side=self._side_value(side),
            type=orders_service_pb2.ORDER_TYPE_MARKET,
            client_order_id=f"finam_core_{symbol}_{side}_{int(qty)}",
            comment="finam_core_real_execution",
        )

    def _send_market_order_grpc(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: float | None,
    ) -> FinamOrderResult:
        """Русский комментарий: реальная отправка market order через gRPC Orders API."""
        order = self._build_market_order(symbol=symbol, side=side, qty=qty)
        stub = self._stub_for_orders()
        response = stub.PlaceOrder(order, metadata=self._metadata())

        order_id = (
            getattr(response, "transaction_id", None)
            or getattr(response, "order_id", None)
            or getattr(response, "id", None)
        )

        return FinamOrderResult(
            symbol=symbol,
            side=side,
            qty=qty,
            price=price,
            status="PLACED",
            order_id=str(order_id) if order_id is not None else None,
            raw={"response": str(response)},
        )

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

        try:
            return self._send_market_order_grpc(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
            )
        except Exception as exc:
            return FinamOrderResult(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                status="ERROR",
                reason=str(exc),
                raw={
                    "account_id": self.account_id,
                    "endpoint": self.endpoint,
                    "symbol": symbol,
                    "side": side,
                    "qty": qty,
                    "price": price,
                },
            )
