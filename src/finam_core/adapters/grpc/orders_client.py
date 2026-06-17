# src/finam_core/adapters/grpc/orders_client.py

from __future__ import annotations

from finam_core.risk.futures_real_block_guard_v1 import evaluate_futures_real_block_v1

import os
import time
from finam_core.config.runtime_config import RuntimeConfig
from dataclasses import dataclass
from finam_core.auth.token_manager import FinamTokenManager
from finam_core.execution.real_execution_safety import RealExecutionSafetyLayer
from finam_core.execution.order_ack import OrderAck
from finam_core.execution.order_ack_logger import OrderAckLogger
from finam_core.execution.protective_order_link import ProtectiveOrderLink
from finam_core.execution.protective_order_link_repository import ProtectiveOrderLinkRepository
from typing import Any

import grpc
from grpc import RpcError
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

    def __init__(self, position_qty_provider=None) -> None:
        self._subscribe_orders_last_error_log_ts = 0.0
        self._subscribe_orders_cooldown_until_ts = 0.0
        self.runtime_config = RuntimeConfig()
        self.account_id = (
            self.runtime_config.get("FINAM_ACCOUNT_ID")
            or self.runtime_config.get("ACCOUNT_ID")
            or self.runtime_config.get("FINAM_ACCOUNT")
            or ""
        ).strip()
        self.token = self.runtime_config.get("FINAM_TOKEN", "").strip()
        self.token_manager = FinamTokenManager()
        self.endpoint = self.runtime_config.get("FINAM_GRPC_ENDPOINT", "api.finam.ru:443").strip()
        self._channel: Any | None = None
        self._stub: Any | None = None
        self.order_ack_logger = OrderAckLogger()
        self.protective_link_repository = ProtectiveOrderLinkRepository()
        self.position_qty_provider = position_qty_provider

    def _validate(self, symbol: str, side: str, qty: float) -> str | None:
        if not self.account_id:
            return "FINAM_ACCOUNT_ID_not_set"
        if not symbol:
            return "symbol_not_set"
        if side not in ("BUY", "SELL"):
            return "invalid_side"
        if qty <= 0:
            return "invalid_qty"
        return None

    def _ensure_token(self) -> str | None:
        """Русский комментарий: получает JWT только после прохождения safe-флагов real execution."""
        self.token = self.token_manager.get_token()
        if not self.token:
            return "FINAM_TOKEN_not_set"
        if self.token.count(".") != 2:
            return "FINAM_TOKEN_not_jwt"
        return None

    def _metadata(self) -> list[tuple[str, str]]:
        """Русский комментарий: metadata всегда должна содержать JWT, а не пустой Bearer."""
        token_error = self._ensure_token()
        if token_error:
            return [("authorization", "Bearer ")]
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

    def get_orders(self) -> list:
        """Русский комментарий: получает текущие заявки брокера через OrdersService.GetOrders."""
        orders_service_pb2, _, _ = self._load_orders_grpc()
        request = orders_service_pb2.OrdersRequest(account_id=self.account_id)
        response = self._stub_for_orders().GetOrders(request, metadata=self._metadata())
        return list(getattr(response, "orders", []) or [])

    def _side_value(self, side: str):
        """Русский комментарий: подбирает enum Side по фактическим именам в proto."""
        _, _, side_pb2 = self._load_orders_grpc()
        for name in (side, f"SIDE_{side}", f"ORDER_SIDE_{side}", f"BUY_SELL_{side}"):
            if hasattr(side_pb2, name):
                return getattr(side_pb2, name)
        raise RuntimeError("orders_side_enum_not_found")


    def _valid_before_from_env(self, orders_pb2):
        """Русский комментарий: срок действия заявки из ENV, по умолчанию до конца дня."""
        value = os.getenv("REAL_ORDER_VALID_BEFORE", "end_of_day").strip().lower()

        if value in {"gtc", "good_till_cancel", "good_till_cancelled"}:
            return orders_pb2.VALID_BEFORE_GOOD_TILL_CANCEL

        return orders_pb2.VALID_BEFORE_END_OF_DAY

    def _make_client_order_id(self) -> str:
        """Русский комментарий: генерирует короткий client_order_id для Finam Orders API."""
        return f"fc{int(__import__('time').time() * 1000) % 100000000000000000}"

    def _build_market_order(self, symbol: str, side: str, qty: float, client_order_id: str | None = None):
        """Русский комментарий: строит Order для OrdersService.PlaceOrder."""
        orders_service_pb2, _, _ = self._load_orders_grpc()
        return orders_service_pb2.Order(
            account_id=self.account_id,
            symbol=symbol,
            quantity=decimal_pb2.Decimal(value=str(int(qty))),
            side=self._side_value(side),
            type=orders_service_pb2.ORDER_TYPE_MARKET,
            time_in_force=orders_service_pb2.TIME_IN_FORCE_DAY,
            valid_before=self._valid_before_from_env(orders_service_pb2),
            client_order_id=client_order_id or self._make_client_order_id(),
            comment="finam_core_real_execution",
        )

    def _build_limit_order(self, symbol: str, side: str, qty: float, limit_price: float):
        """Русский комментарий: строит LIMIT Order для OrdersService.PlaceOrder."""
        orders_service_pb2, _, _ = self._load_orders_grpc()
        return orders_service_pb2.Order(
            account_id=self.account_id,
            symbol=symbol,
            quantity=decimal_pb2.Decimal(value=str(int(qty))),
            side=self._side_value(side),
            type=orders_service_pb2.ORDER_TYPE_LIMIT,
            limit_price=decimal_pb2.Decimal(value=str(float(limit_price))),
            time_in_force=orders_service_pb2.TIME_IN_FORCE_DAY,
            valid_before=self._valid_before_from_env(orders_service_pb2),
            client_order_id=client_order_id or self._make_client_order_id(),
            comment="finam_core_limit_order",
        )


    def _build_stop_order(self, symbol: str, side: str, qty: float, stop_price: float, client_order_id: str | None = None):
        """Русский комментарий: сборка STOP-заявки Finam без отправки брокеру."""
        orders_service_pb2, _, side_pb2 = self._load_orders_grpc()

        side_u = str(side or "").upper()
        if side_u not in ("BUY", "SELL"):
            raise ValueError(f"unsupported stop order side: {side}")

        if float(qty or 0.0) <= 0:
            raise ValueError("stop order qty must be positive")

        if float(stop_price or 0.0) <= 0:
            raise ValueError("stop_price must be positive")

        order = orders_service_pb2.Order()
        order.account_id = self.account_id
        order.symbol = str(symbol)
        order.quantity.value = str(float(qty)).rstrip("0").rstrip(".")
        order.side = side_pb2.SIDE_BUY if side_u == "BUY" else side_pb2.SIDE_SELL
        order.type = orders_service_pb2.ORDER_TYPE_STOP
        order.stop_price.value = str(float(stop_price))
        order.stop_condition = (
            orders_service_pb2.STOP_CONDITION_LAST_DOWN
            if side_u == "SELL"
            else orders_service_pb2.STOP_CONDITION_LAST_UP
        )
        order.time_in_force = orders_service_pb2.TIME_IN_FORCE_DAY
        order.valid_before = self._valid_before_from_env(orders_service_pb2)
        order.client_order_id = client_order_id or self._make_client_order_id()
        order.comment = "finam_core_trailing_stop"
        return order


    def set_position_qty_provider(self, position_qty_provider) -> None:
        """Русский комментарий: подключает источник broker/local позиции из Portfolio/PositionManager."""
        self.position_qty_provider = position_qty_provider

    def _resolve_position_qty_pair(self, symbol: str) -> tuple[float | None, float | None]:
        """Русский комментарий: получает broker/local qty перед real PlaceOrder без env-подмены."""
        provider = getattr(self, "position_qty_provider", None)
        if provider is None:
            return None, None

        try:
            if hasattr(provider, "get_position_qty_pair"):
                pair = provider.get_position_qty_pair(symbol)
            elif callable(provider):
                pair = provider(symbol)
            else:
                return None, None

            if isinstance(pair, dict):
                broker_qty = pair.get("broker_qty")
                local_qty = pair.get("local_qty")
            else:
                broker_qty, local_qty = pair

            return float(broker_qty), float(local_qty)
        except Exception as exc:
            print(f"POSITION_QTY_PROVIDER_FAILED symbol={symbol} error={exc}", flush=True)
            return None, None

    def _assert_real_execution_safety(self, order) -> None:
        """Русский комментарий: финальный предохранитель непосредственно перед real PlaceOrder."""
        symbol = str(getattr(order, "symbol", "") or "")
        side_raw = getattr(order, "side", "")
        side = str(side_raw)

        if isinstance(side_raw, int):
            side = "BUY" if side_raw == 1 else "SELL" if side_raw == 2 else str(side_raw)

        qty_obj = getattr(order, "quantity", None)
        qty = 0.0
        try:
            qty = float(getattr(qty_obj, "value", qty_obj) or 0.0)
        except Exception:
            qty = 0.0

        broker_position_qty, local_position_qty = self._resolve_position_qty_pair(symbol)

        safety_decision = RealExecutionSafetyLayer().check(
            symbol=symbol,
            side=side,
            qty=qty,
            execution_mode="real",
            broker_position_qty=broker_position_qty,
            local_position_qty=local_position_qty,
        )
        if not safety_decision.allowed:
            print(
                f"REAL_EXECUTION_SAFETY_BLOCK symbol={symbol} side={side} qty={qty} reason={safety_decision.reason}",
                flush=True,
            )
            raise RuntimeError(f"REAL_EXECUTION_SAFETY_BLOCK:{safety_decision.reason}")

    def _build_order_ack(self, *, response, symbol: str, side: str, qty: float, fallback_status: str = "ACCEPTED") -> OrderAck:
        """Русский комментарий: нормализует broker response после PlaceOrder в единый ACK."""
        order_id = (
            getattr(response, "transaction_id", None)
            or getattr(response, "order_id", None)
            or getattr(response, "id", None)
        )
        status_raw = getattr(response, "status", None)
        status = str(status_raw) if status_raw is not None else fallback_status
        accepted = bool(order_id) or status.upper() in ("ACCEPTED", "PLACED", "NEW", "ORDER_STATUS_NEW")
        reason = None if accepted else "PLACE_ORDER_NO_ACK"

        return OrderAck(
            accepted=accepted,
            symbol=str(symbol),
            side=str(side),
            qty=float(qty),
            order_id=str(order_id) if order_id is not None else None,
            status=status,
            reason=reason,
            raw={"response": str(response)},
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
        self._assert_real_execution_safety(order)
        stub = self._stub_for_orders()
        response = stub.PlaceOrder(order, metadata=self._metadata())

        ack = self._build_order_ack(
            response=response,
            symbol=symbol,
            side=side,
            qty=qty,
            fallback_status="PLACED",
        )
        self.order_ack_logger.log(ack, source="market_order")
        if ack.accepted and ack.order_id:
            self.protective_link_repository.save(
                ProtectiveOrderLink(
                    symbol=symbol,
                    side=side,
                    qty=qty,
                    entry_order_id=ack.order_id,
                    stop_order_id=None,
                    take_order_id=None,
                    status="OPEN",
                    source="market_order_ack",
                    raw={"ack": ack.__dict__},
                )
            )

        return FinamOrderResult(
            symbol=symbol,
            side=side,
            qty=qty,
            price=price,
            status=ack.status,
            order_id=ack.order_id,
            reason=ack.reason,
            raw={"ack": ack.__dict__},
        )

    def _normalize_broker_error(self, exc: Exception) -> tuple[str, dict]:
        """Русский комментарий: нормализует ошибки брокера в стабильные reason-коды."""
        raw_text = str(exc)
        grpc_code = None
        grpc_details = None

        if isinstance(exc, RpcError):
            try:
                grpc_code = str(exc.code())
            except Exception:
                grpc_code = None
            try:
                grpc_details = str(exc.details())
            except Exception:
                grpc_details = None

        text = grpc_details or raw_text

        if "[666]" in text or "uncovered position" in text.lower() or "непокрыт" in text.lower():
            return "BROKER_UNCOVERED_POSITION_WARNING", {
                "grpc_code": grpc_code,
                "grpc_details": grpc_details,
                "raw_error": raw_text,
                "retryable": False,
            }

        if "No enough coverage" in text or "Недостаток обеспечения" in text:
            return "BROKER_NOT_ENOUGH_COVERAGE", {
                "grpc_code": grpc_code,
                "grpc_details": grpc_details,
                "raw_error": raw_text,
                "retryable": False,
            }

        if "Trading is not available at the moment" in text:
            return "BROKER_TRADING_NOT_AVAILABLE", {
                "grpc_code": grpc_code,
                "grpc_details": grpc_details,
                "raw_error": raw_text,
                "retryable": False,
            }

        if "Market orders are not permitted" in text or "рыночн" in text.lower():
            return "BROKER_MARKET_ORDERS_NOT_PERMITTED", {
                "grpc_code": grpc_code,
                "grpc_details": grpc_details,
                "raw_error": raw_text,
                "retryable": False,
            }

        return str(exc), {
            "grpc_code": grpc_code,
            "grpc_details": grpc_details,
            "raw_error": raw_text,
            "retryable": False,
        }

    def _normalize_order_stream_event(self, item, orders_pb2, side_pb2) -> dict:
        """Русский комментарий: нормализует событие SubscribeOrders без зависимости от точного wrapper-типа."""
        # Русский комментарий: item может быть либо самим OrderState, либо wrapper-ответом SubscribeOrdersResponse.
        if hasattr(item, "status") and hasattr(item, "order_id"):
            state = item
        else:
            state = getattr(item, "state", None) or getattr(item, "order_state", None) or item
        order = getattr(state, "order", None)

        symbol = str(getattr(order, "symbol", "") or "") if order is not None else ""
        status = self._enum_name(orders_pb2.OrderStatus, getattr(state, "status", 0)).replace("ORDER_STATUS_", "")
        side = self._enum_name(side_pb2.Side, getattr(order, "side", 0)).replace("SIDE_", "") if order is not None else ""
        order_type = self._enum_name(orders_pb2.OrderType, getattr(order, "type", 0)).replace("ORDER_TYPE_", "") if order is not None else ""

        quantity = getattr(order, "quantity", None) if order is not None else None
        qty = float(getattr(quantity, "value", 0.0) or 0.0)

        limit_price = getattr(order, "limit_price", None) if order is not None else None
        stop_price = getattr(order, "stop_price", None) if order is not None else None

        return {
            "order_id": str(getattr(state, "order_id", "") or ""),
            "exec_id": str(getattr(state, "exec_id", "") or ""),
            "symbol": symbol,
            "side": side,
            "status": status,
            "order_type": order_type,
            "qty": qty,
            "price": getattr(limit_price, "value", None),
            "stop_price": getattr(stop_price, "value", None),
            "raw": {"event_repr": str(item)},
        }

    def subscribe_orders(self, *, max_events: int | None = None) -> list[dict]:
        """Русский комментарий: read-only SubscribeOrders. Возвращает нормализованные события заявок."""
        events: list[dict] = []

        now_ts = time.time()
        cooldown_until = float(getattr(self, "_subscribe_orders_cooldown_until_ts", 0.0) or 0.0)
        if cooldown_until and now_ts < cooldown_until:
            return events

        try:
            if not self.account_id:
                print("FINAM_SUBSCRIBE_ORDERS_NO_ACCOUNT_ID", flush=True)
                return events

            orders_pb2, _, side_pb2 = self._load_orders_grpc()
            req = orders_pb2.SubscribeOrdersRequest(account_id=str(self.account_id))

            stream = self._stub_for_orders().SubscribeOrders(
                req,
                metadata=self._metadata(),
                timeout=float(os.getenv("FINAM_SUBSCRIBE_ORDERS_TIMEOUT_SEC", "30")),
            )

            limit = int(max_events or int(os.getenv("FINAM_SUBSCRIBE_ORDERS_MAX_EVENTS", "1")))
            for item in stream:
                event = self._normalize_order_stream_event(item, orders_pb2, side_pb2)
                events.append(event)
                if len(events) >= limit:
                    break

            return events

        except Exception as exc:
            now_ts = time.time()
            heartbeat = float(os.getenv("SUBSCRIBE_ORDERS_ERROR_HEARTBEAT_SEC", "300"))
            cooldown = float(os.getenv("SUBSCRIBE_ORDERS_ERROR_COOLDOWN_SEC", "60"))
            last_ts = float(getattr(self, "_subscribe_orders_last_error_log_ts", 0.0) or 0.0)

            if not last_ts or now_ts - last_ts >= heartbeat:
                print(f"FINAM_SUBSCRIBE_ORDERS_ERROR error={exc}", flush=True)
                self._subscribe_orders_last_error_log_ts = now_ts

            self._subscribe_orders_cooldown_until_ts = now_ts + cooldown
            return events


    def cancel_order(self, order_id: str) -> dict:
        """Русский комментарий: отмена заявки; без подтверждения работает как dry-run."""
        if not order_id:
            return {"status": "REJECTED", "reason": "empty_order_id"}

        if not self.runtime_config.get_bool("REAL_EXECUTION_ENABLED", False) or not self.runtime_config.get_bool("REAL_ORDER_CONFIRM", False):
            return {"status": "DRY_RUN_CANCEL", "order_id": order_id, "reason": "real_order_confirm_disabled"}

        try:
            orders_pb2, _, _ = self._load_orders_grpc()
            req = orders_pb2.CancelOrderRequest(
                account_id=str(self.account_id),
                order_id=str(order_id),
            )
            self._stub_for_orders().CancelOrder(
                req,
                metadata=self._metadata(),
                timeout=float(os.getenv("FINAM_CANCEL_ORDER_TIMEOUT_SEC", "10")),
            )
            return {"status": "CANCELED", "order_id": order_id}
        except Exception as exc:
            reason, raw = self._normalize_broker_error(exc)
            return {"status": "REJECTED", "order_id": order_id, "reason": reason, "raw": raw}

    def place_stop_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        stop_price: float,
        client_order_id: str | None = None,
    ) -> dict:
        """Русский комментарий: постановка стоп-заявки; без подтверждения работает как dry-run."""
        err = self._validate(symbol, side, qty)
        if err:
            return {"status": "REJECTED", "reason": err}

        try:
            stop_price = float(stop_price)
        except Exception:
            return {"status": "REJECTED", "reason": "invalid_stop_price"}

        if stop_price <= 0:
            return {"status": "REJECTED", "reason": "invalid_stop_price"}

        if not self.runtime_config.get_bool("REAL_EXECUTION_ENABLED", False) or not self.runtime_config.get_bool("REAL_ORDER_CONFIRM", False):
            return {
                "status": "DRY_RUN_ACCEPTED",
                "symbol": symbol,
                "side": side,
                "qty": float(qty),
                "stop_price": stop_price,
                "order_id": f"dry_stop_{symbol}_{side}_{qty}_{stop_price}",
                "reason": "real_order_confirm_disabled",
            }

        try:
            order = self._build_stop_order(
                symbol=symbol,
                side=side,
                qty=qty,
                stop_price=stop_price,
                client_order_id=client_order_id or self._make_client_order_id(),
            )
            self._assert_real_execution_safety(order)
            resp = self._stub_for_orders().PlaceOrder(
                order,
                metadata=self._metadata(),
                timeout=float(os.getenv("FINAM_PLACE_STOP_TIMEOUT_SEC", "10")),
            )
            ack = self._build_order_ack(
                response=resp,
                symbol=symbol,
                side=side,
                qty=qty,
                fallback_status="ACCEPTED",
            )
            self.order_ack_logger.log(ack, source="stop_order")
            if ack.accepted and ack.order_id:
                self.protective_link_repository.attach_protective_order(
                    symbol=symbol,
                    side=side,
                    qty=qty,
                    order_id=ack.order_id,
                    protective_type="stop",
                )
            return {
                "status": ack.status,
                "symbol": symbol,
                "side": side,
                "qty": float(qty),
                "stop_price": stop_price,
                "order_id": ack.order_id,
                "reason": ack.reason,
                "raw": {"ack": ack.__dict__},
            }
        except Exception as exc:
            reason, raw = self._normalize_broker_error(exc)
            return {
                "status": "REJECTED",
                "symbol": symbol,
                "side": side,
                "qty": float(qty),
                "stop_price": stop_price,
                "reason": reason,
                "raw": raw,
            }


    def place_limit_order(self, symbol: str, side: str, qty: float, limit_price: float, client_order_id: str | None = None) -> dict:
        """Русский комментарий: постановка лимитной заявки; без подтверждения работает как dry-run."""
        err = self._validate(symbol, side, qty)
        if err:
            return {"status": "REJECTED", "reason": err}

        try:
            limit_price = float(limit_price)
        except Exception:
            return {"status": "REJECTED", "reason": "invalid_limit_price"}

        if limit_price <= 0:
            return {"status": "REJECTED", "reason": "invalid_limit_price"}

        if not self.runtime_config.get_bool("REAL_EXECUTION_ENABLED", False) or not self.runtime_config.get_bool("REAL_ORDER_CONFIRM", False):
            return {
                "status": "DRY_RUN_ACCEPTED",
                "symbol": symbol,
                "side": side,
                "qty": float(qty),
                "limit_price": limit_price,
                "order_id": f"dry_limit_{symbol}_{side}_{qty}_{limit_price}",
                "reason": "real_order_confirm_disabled",
            }

        # LOW_LEVEL_GRPC_ORDER_CLIENT_LAST_LINE_GUARD_V1
        # Русский комментарий:
        # Последняя линия защиты на уровне gRPC orders_client.
        # Если кто-то обойдёт верхние execution-адаптеры, real futures всё равно
        # не должны уйти в PlaceOrder до 01.07.2026.
        guard_decision = evaluate_futures_real_block_v1(
            symbol=symbol,
            execution_mode="real",
        )
        if not guard_decision.allowed:
            print(
                "LOW_LEVEL_GRPC_ORDER_CLIENT_LAST_LINE_GUARD_BLOCKED "
                f"symbol={guard_decision.symbol} "
                f"side={side} "
                f"mode={guard_decision.execution_mode} "
                f"kind={guard_decision.instrument_kind} "
                f"reason={guard_decision.reason} "
                f"current_date={guard_decision.current_date} "
                f"allowed_after={guard_decision.allowed_after}",
                flush=True,
            )
            return {
                "status": "REJECTED",
                "symbol": symbol,
                "side": side,
                "qty": float(qty),
                "limit_price": limit_price,
                "order_id": None,
                "reason": guard_decision.reason,
                "raw": {
                    "futures_real_block_guard": True,
                    "place_order_sent": False,
                    "allowed_after": str(guard_decision.allowed_after),
                },
            }

        try:
            order = self._build_limit_order(
                symbol=symbol,
                side=side,
                qty=qty,
                limit_price=limit_price,
            )
            self._assert_real_execution_safety(order)
            resp = self._stub_for_orders().PlaceOrder(
                order,
                metadata=self._metadata(),
                timeout=float(os.getenv("FINAM_PLACE_LIMIT_TIMEOUT_SEC", "10")),
            )
            ack = self._build_order_ack(
                response=resp,
                symbol=symbol,
                side=side,
                qty=qty,
                fallback_status="ACCEPTED",
            )
            self.order_ack_logger.log(ack, source="limit_order")
            if ack.accepted and ack.order_id:
                self.protective_link_repository.attach_protective_order(
                    symbol=symbol,
                    side=side,
                    qty=qty,
                    order_id=ack.order_id,
                    protective_type="take",
                )
            return {
                "status": ack.status,
                "symbol": symbol,
                "side": side,
                "qty": float(qty),
                "limit_price": limit_price,
                "order_id": ack.order_id,
                "reason": ack.reason,
                "raw": {"ack": ack.__dict__},
            }
        except Exception as exc:
            reason, raw = self._normalize_broker_error(exc)
            return {
                "status": "REJECTED",
                "symbol": symbol,
                "side": side,
                "qty": float(qty),
                "limit_price": limit_price,
                "reason": reason,
                "raw": raw,
            }


    def place_market_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: float | None = None,
        client_order_id: str | None = None,
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

        if not self.runtime_config.get_bool("REAL_ORDER_CONFIRM", False):
            ack = OrderAck(
                accepted=True,
                symbol=symbol,
                side=side,
                qty=float(qty),
                order_id=f"dry_market_{symbol}_{side}_{qty}",
                status="DRY_RUN_ACCEPTED",
                reason="real_order_confirm_disabled",
                raw={"dry_run": True, "place_order_sent": False},
            )
            self.order_ack_logger.log(ack, source="market_order_dry_run")

            return FinamOrderResult(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                status=ack.status,
                order_id=ack.order_id,
                reason=ack.reason,
                raw={"ack": ack.__dict__},
            )

        # LOW_LEVEL_GRPC_ORDER_CLIENT_LAST_LINE_GUARD_V1
        # Русский комментарий:
        # Последняя линия защиты на уровне gRPC orders_client для market-заявки.
        # Блокируем real futures до 01.07.2026 непосредственно перед token/send path.
        guard_decision = evaluate_futures_real_block_v1(
            symbol=symbol,
            execution_mode="real",
        )
        if not guard_decision.allowed:
            print(
                "LOW_LEVEL_GRPC_ORDER_CLIENT_LAST_LINE_GUARD_BLOCKED "
                f"symbol={guard_decision.symbol} "
                f"side={side} "
                f"mode={guard_decision.execution_mode} "
                f"kind={guard_decision.instrument_kind} "
                f"reason={guard_decision.reason} "
                f"current_date={guard_decision.current_date} "
                f"allowed_after={guard_decision.allowed_after}",
                flush=True,
            )
            return FinamOrderResult(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                status="REJECTED",
                reason=guard_decision.reason,
                raw={
                    "futures_real_block_guard": True,
                    "place_order_sent": False,
                    "allowed_after": str(guard_decision.allowed_after),
                },
            )

        token_reason = self._ensure_token()
        if token_reason:
            return FinamOrderResult(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                status="REJECTED",
                reason=token_reason,
            )

        try:
            return self._send_market_order_grpc(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
            )
        except Exception as exc:
            reason, error_raw = self._normalize_broker_error(exc)
            error_raw.update(
                {
                    "account_id": self.account_id,
                    "endpoint": self.endpoint,
                    "symbol": symbol,
                    "side": side,
                    "qty": qty,
                    "price": price,
                }
            )
            return FinamOrderResult(
                symbol=symbol,
                side=side,
                qty=qty,
                price=price,
                status="ERROR",
                reason=reason,
                raw=error_raw,
            )


    def _enum_name(self, enum_type, value) -> str:
        """Русский комментарий: безопасно преобразует protobuf enum number в имя."""
        try:
            return enum_type.Name(int(value))
        except Exception:
            return str(value)


    def list_open_orders(self) -> list[dict]:
        """Русский комментарий: read-only получение активных заявок брокера через Finam Orders GetOrders."""
        try:
            if not self.account_id:
                print("FINAM_OPEN_ORDERS_NO_ACCOUNT_ID", flush=True)
                return []

            orders_pb2, _, side_pb2 = self._load_orders_grpc()
            req = orders_pb2.OrdersRequest(account_id=str(self.account_id))
            resp = self._stub_for_orders().GetOrders(
                req,
                metadata=self._metadata(),
                timeout=float(os.getenv("FINAM_OPEN_ORDERS_TIMEOUT_SEC", "10")),
            )

            result = []
            active_statuses = {"WATCHING", "ACTIVE", "WORKING", "ACCEPTED", "NEW", "PARTIAL_FILLED"}

            for state in getattr(resp, "orders", []) or []:
                order = getattr(state, "order", None)
                symbol = str(getattr(order, "symbol", "") or "") if order is not None else ""

                status = self._enum_name(
                    orders_pb2.OrderStatus,
                    getattr(state, "status", 0),
                ).replace("ORDER_STATUS_", "")
                side = self._enum_name(
                    side_pb2.Side,
                    getattr(order, "side", 0),
                ).replace("SIDE_", "") if order is not None else ""
                order_type = self._enum_name(
                    orders_pb2.OrderType,
                    getattr(order, "type", 0),
                ).replace("ORDER_TYPE_", "") if order is not None else ""

                quantity = getattr(order, "quantity", None) if order is not None else None
                qty = float(getattr(quantity, "value", 0.0) or 0.0)

                limit_price = getattr(order, "limit_price", None) if order is not None else None
                stop_price = getattr(order, "stop_price", None) if order is not None else None

                if status not in active_statuses:
                    continue

                if not symbol:
                    continue

                result.append({
                    "order_id": str(getattr(state, "order_id", "") or ""),
                    "exec_id": str(getattr(state, "exec_id", "") or ""),
                    "symbol": symbol,
                    "side": side,
                    "status": status,
                    "order_type": order_type,
                    "qty": qty,
                    "price": getattr(limit_price, "value", None),
                    "stop_price": getattr(stop_price, "value", None),
                    "raw": {"state_repr": str(state)},
                })

            if os.getenv("FINAM_OPEN_ORDERS_DEBUG", "0") == "1":
                print(f"FINAM_OPEN_ORDERS_LOADED active_count={len(result)}", flush=True)
            return result

        except Exception as exc:
            print(f"FINAM_OPEN_ORDERS_LIST_ERROR error={exc}", flush=True)
            return []


    def get_open_orders(self) -> list[dict]:
        """Русский комментарий: совместимый alias для OpenOrdersSync."""
        return self.list_open_orders()
