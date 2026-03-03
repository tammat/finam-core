# src/infra/brokers/finam_rest.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import os
import requests

from .base import BrokerAdapter


class FinamRestError(RuntimeError):
    pass


@dataclass(frozen=True)
class FinamRestRoutes:
    # ВАЖНО: сейчас у тебя "Route not found". Поэтому держим маршруты в одном месте.
    # Как только поддержка/доки подтвердят — правим только тут.
    accounts: str = "/api/v1/accounts"
    portfolio: str = "/api/v1/portfolio"
    orders: str = "/api/v1/orders"
    place_order: str = "/api/v1/orders"
    cancel_order: str = "/api/v1/orders/{order_id}"


@dataclass
class FinamRestConfig:
    base_url: str
    token: str
    timeout: float = 15.0
    routes: FinamRestRoutes = FinamRestRoutes()

    @staticmethod
    def from_env() -> "FinamRestConfig":
        base_url = os.getenv("FINAM_REST_BASE", "https://tradeapi.finam.ru").rstrip("/")
        token = os.getenv("FINAM_TOKEN", "").strip()
        if not token:
            raise FinamRestError("FINAM_TOKEN is empty")
        timeout = float(os.getenv("FINAM_TIMEOUT", "15"))
        return FinamRestConfig(base_url=base_url, token=token, timeout=timeout)


class FinamRestBrokerAdapter(BrokerAdapter):
    """
    REST адаптер под BrokerAdapter.

    Делаем максимально "тонким":
    - только HTTP + нормализация ответа
    - никакой бизнес-логики
    """

    def __init__(self, cfg: FinamRestConfig):
        self.cfg = cfg
        self._session = requests.Session()

    def start(self) -> None:
        # REST не требует persistent start, но сессия уже готова
        return None

    def stop(self) -> None:
        self._session.close()

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.cfg.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _url(self, path: str) -> str:
        return f"{self.cfg.base_url}{path}"

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None, extra_headers: Optional[Dict[str, str]] = None) -> Any:
        h = self._headers()
        if extra_headers:
            h.update(extra_headers)

        r = self._session.get(self._url(path), headers=h, params=params, timeout=self.cfg.timeout, allow_redirects=True)
        if r.status_code >= 400:
            raise FinamRestError(f"GET {path} -> {r.status_code}: {r.text}")
        return r.json() if r.text else None

    def _post(self, path: str, payload: Dict[str, Any], extra_headers: Optional[Dict[str, str]] = None) -> Any:
        h = self._headers()
        if extra_headers:
            h.update(extra_headers)

        r = self._session.post(self._url(path), headers=h, json=payload, timeout=self.cfg.timeout, allow_redirects=True)
        if r.status_code >= 400:
            raise FinamRestError(f"POST {path} -> {r.status_code}: {r.text}")
        return r.json() if r.text else None

    def _delete(self, path: str, extra_headers: Optional[Dict[str, str]] = None) -> Any:
        h = self._headers()
        if extra_headers:
            h.update(extra_headers)

        r = self._session.delete(self._url(path), headers=h, timeout=self.cfg.timeout, allow_redirects=True)
        if r.status_code >= 400:
            raise FinamRestError(f"DELETE {path} -> {r.status_code}: {r.text}")
        return r.json() if r.text else None

    # --- BrokerAdapter API ---

    def get_accounts(self) -> List[Dict[str, Any]]:
        # если 404 — значит маршрут другой; но интерфейс готов
        data = self._get(self.cfg.routes.accounts)
        # нормализация: ожидаем список
        if data is None:
            return []
        if isinstance(data, list):
            return data
        # иногда API отдаёт {"accounts":[...]}
        if isinstance(data, dict) and "accounts" in data and isinstance(data["accounts"], list):
            return data["accounts"]
        return [data]

    def get_positions(self, account_id: str) -> List[Dict[str, Any]]:
        # портфель/позиции
        data = self._get(self.cfg.routes.portfolio, params={"accountId": account_id})
        if not data:
            return []
        # под разные форматы
        if isinstance(data, dict) and "positions" in data:
            return data["positions"] or []
        if isinstance(data, list):
            return data
        return [data]

    def get_orders(self, account_id: str) -> List[Dict[str, Any]]:
        data = self._get(self.cfg.routes.orders, params={"accountId": account_id})
        if not data:
            return []
        if isinstance(data, dict) and "orders" in data:
            return data["orders"] or []
        if isinstance(data, list):
            return data
        return [data]

    def place_order(
        self,
        account_id: str,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
        price: float | None = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "accountId": account_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "type": order_type,
        }
        if price is not None:
            payload["price"] = price

        return self._post(self.cfg.routes.place_order, payload)

    def cancel_order(self, account_id: str, order_id: str) -> Dict[str, Any]:
        path = self.cfg.routes.cancel_order.format(order_id=order_id)
        # некоторые API требуют accountId даже на cancel — добавим header/params при необходимости
        return self._delete(path)

    def subscribe_quotes(self, symbols: List[str]) -> None:
        # REST: no-op (подписки через WS/gRPC)
        return None

    def unsubscribe_quotes(self, symbols: List[str]) -> None:
        return None