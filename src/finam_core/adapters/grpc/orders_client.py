# src/finam_core/adapters/grpc/orders_client.py

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import grpc


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
            from finam_proto.grpc.tradeapi.v1 import orders_pb2, orders_pb2_grpc  # type: ignore
            return orders_pb2, orders_pb2_grpc
        except Exception as exc:
            raise RuntimeError(f"orders_grpc_modules_not_available: {exc}") from exc

    def _stub_for_orders(self):
        """Русский комментарий: создаёт gRPC stub только при подтверждённом real-вызове."""
        if self._stub is not None:
            return self._stub

        _, orders_pb2_grpc = self._load_orders_grpc()
        self._channel = grpc.secure_channel(self.endpoint, grpc.ssl_channel_credentials())

        if hasattr(orders_pb2_grpc, "OrdersStub"):
            self._stub = orders_pb2_grpc.OrdersStub(self._channel)
            return self._stub

        if hasattr(orders_pb2_grpc, "OrdersServiceStub"):
            self._stub = orders_pb2_grpc.OrdersServiceStub(self._channel)
            return self._stub

        raise RuntimeError("orders_stub_class_not_found")

    def _split_symbol(self, symbol: str) -> tuple[str, str]:
        """Русский комментарий: BRM6@RTSX -> (BRM6, RTSX)."""
        if "@" not in symbol:
            raise ValueError("symbol_must_be_CODE@BOARD")
        code, board = symbol.split("@", 1)
        if not code or not board:
            raise ValueError("symbol_must_be_CODE@BOARD")
        return code, board

    def _build_market_order_request(self, symbol: str, side: str, qty: float):
        """Русский комментарий: строит protobuf-запрос market order по доступной схеме proto."""
        orders_pb2, _ = self._load_orders_grpc()
        code, board = self._split_symbol(symbol)

        request_cls = None
        for name in ("NewOrderRequest", "PlaceOrderRequest", "CreateOrderRequest"):
            if hasattr(orders_pb2, name):
                request_cls = getattr(orders_pb2, name)
                break
        if request_cls is None:
            raise RuntimeError("orders_request_class_not_found")

        side_value = None
        for enum_name in (side, f"ORDER_SIDE_{side}", f"BUY_SELL_{side}"):
            if hasattr(orders_pb2, enum_name):
                side_value = getattr(orders_pb2, enum_name)
                break

        if side_value is None:
            if side == "BUY" and hasattr(orders_pb2, "BUY"):
                side_value = getattr(orders_pb2, "BUY")
            elif side == "SELL" and hasattr(orders_pb2, "SELL"):
                side_value = getattr(orders_pb2, "SELL")
            else:
                raise RuntimeError("orders_side_enum_not_found")

        market_value = None
        for enum_name in ("MARKET", "ORDER_TYPE_MARKET", "PROPERTY_MARKET"):
            if hasattr(orders_pb2, enum_name):
                market_value = getattr(orders_pb2, enum_name)
                break

        candidates = [
            {
                "client_id": self.account_id,
                "security_board": board,
                "security_code": code,
                "buy_sell": side_value,
                "quantity": int(qty),
                "use_credit": False,
            },
            {
                "account_id": self.account_id,
                "board": board,
                "symbol": code,
                "side": side_value,
                "quantity": int(qty),
            },
        ]

        if market_value is not None:
            candidates[0]["property"] = market_value
            candidates[1]["order_type"] = market_value

        last_error = None
        for kwargs in candidates:
            try:
                return request_cls(**kwargs)
            except Exception as exc:
                last_error = exc

        raise RuntimeError(f"orders_request_build_failed: {last_error}")

    def _send_market_order_grpc(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: float | None,
    ) -> FinamOrderResult:
        """Русский комментарий: реальная отправка market order через gRPC Orders API."""
        request = self._build_market_order_request(symbol, side, qty)
        stub = self._stub_for_orders()

        method = None
        for method_name in ("NewOrder", "PlaceOrder", "CreateOrder"):
            if hasattr(stub, method_name):
                method = getattr(stub, method_name)
                break

        if method is None:
            raise RuntimeError("orders_place_method_not_found")

        response = method(request, metadata=self._metadata())

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
