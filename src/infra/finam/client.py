# finam_bot/finam_client.py

import os
os.environ["GRPC_DNS_RESOLVER"] = "native"
from datetime import datetime, timedelta, timezone,time as dt_time
from pathlib import Path
from finam_bot.clients import schema
from typing import Any, Callable, Dict, List, Optional
import time
import grpc
from dotenv import load_dotenv
from google.type import interval_pb2
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf import timestamp_pb2
#from datetime import datetime, time as dt_time
# --- gRPC stubs ---
from finam_bot.grpc_api.grpc.tradeapi.v1.accounts import (
    accounts_service_pb2,
    accounts_service_pb2_grpc,
)
from finam_bot.grpc_api.grpc.tradeapi.v1.orders import (
    orders_service_pb2,
    orders_service_pb2_grpc,
)
from finam_bot.grpc_api.grpc.tradeapi.v1.marketdata import (
    marketdata_service_pb2_grpc,
)
from finam_bot.grpc_api.grpc.tradeapi.v1.auth import (
    auth_service_pb2,
    auth_service_pb2_grpc,
)
from finam_bot.grpc_api.grpc.tradeapi.v1.orders import orders_service_pb2
from finam_bot.grpc_api.grpc.tradeapi.v1 import side_pb2
from google.type import decimal_pb2
from datetime import datetime
import pytz



# -------------------------------------------------
# ENV
# -------------------------------------------------

def _load_env_once() -> None:
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)


_load_env_once()




# -------------------------------------------------
# CLIENT
# -------------------------------------------------
from finam_bot.clients.base import BaseTradingClient

class FinamClient(BaseTradingClient):
    def __init__(self):
        self.execution_enabled = os.getenv("EXECUTION_ENABLED", "0") == "1"
        self.mode = os.getenv("MODE", "REAL").upper()
        self.api_token = os.getenv("FINAM_TOKEN")
        self.account_id = os.getenv("FINAM_ACCOUNT_ID")
        self._tech_window = False
        if not self.api_token:
            raise RuntimeError("FINAM_TOKEN not set")

        if not self.account_id:
            raise RuntimeError("FINAM_ACCOUNT_ID not set")

        # --- host ---
        if self.mode == "TEST":
            self.host = "sandbox-api.finam.ru:443"
        else:
            self.host = "api.finam.ru:443"

        creds = grpc.ssl_channel_credentials()
        self.channel = grpc.secure_channel(self.host, creds)

        # --- Auth ---
        self._auth_stub = auth_service_pb2_grpc.AuthServiceStub(self.channel)
        self.jwt_token = self._exchange_token()

        self.metadata = [("authorization", f"Bearer {self.jwt_token}")]

        # --- Services ---
        self.accounts = accounts_service_pb2_grpc.AccountsServiceStub(self.channel)
        self.orders = orders_service_pb2_grpc.OrdersServiceStub(self.channel)
        self.marketdata = marketdata_service_pb2_grpc.MarketDataServiceStub(self.channel)

        print("✅ FinamClient initialized")
        print("Host:", self.host)
        print("Account ID:", self.account_id)
        print("JWT length:", len(self.jwt_token))

    # -------------------------------------------------
    def get_portfolios(self):
        raw = self.get_portfolios_raw()
        portfolios = raw["portfolios"]

        for p in portfolios:
            schema.validate_row(p, schema.PORTFOLIO_FIELDS, "PORTFOLIO")

        return portfolios

    def _exchange_token(self) -> str:
        """
        Обменивает API токен на session JWT через AuthService
        С retry и backoff
        """

        max_attempts = 3
        delay = 1.0

        req = auth_service_pb2.AuthRequest(secret=self.api_token)

        for attempt in range(1, max_attempts + 1):
            try:
                resp = self._auth_stub.Auth(req)
                return resp.token

            except grpc.RpcError as e:
                print(f"Auth attempt {attempt} failed:", e)

                if attempt == max_attempts:
                    raise

                time.sleep(delay)
                delay *= 2  # экспоненциальный backoff
    # -------------------------------------------------
    def _rpc_call_exec(self, fn, request, *, timeout=5.0, retries=0):
        """
        Execution-safe RPC call.
        retries=0 for PlaceOrder (idempotency risk)
        retries>0 allowed only for safe operations (Cancel/Get)
        """
        last_exc = None
        from finam_bot.system.health_monitor import HealthMonitor

        self.health = HealthMonitor()

        for attempt in range(retries + 1):
            try:
                return fn(request, metadata=self.metadata, timeout=timeout)

            except grpc.RpcError as e:
                code = e.code()
                details = e.details()

                # --- transport / network ---
                if code in (
                        grpc.StatusCode.UNAVAILABLE,
                        grpc.StatusCode.DEADLINE_EXCEEDED,
                        grpc.StatusCode.INTERNAL,
                ):
                    last_exc = TransportError(
                        message="Transport error",
                        code=str(code),
                        details=details,
                        retryable=True,
                        raw=e,
                    )
                    if attempt < retries:
                        continue
                    raise last_exc

                # --- validation / broker errors ---
                if code == grpc.StatusCode.INVALID_ARGUMENT:
                    raise BrokerError(
                        message="Broker rejected request",
                        code=str(code),
                        details=details,
                        retryable=False,
                        raw=e,
                    )

                if code == grpc.StatusCode.PERMISSION_DENIED:
                    raise BrokerError(
                        message="Permission denied",
                        code=str(code),
                        details=details,
                        retryable=False,
                        raw=e,
                    )

                # --- unknown ---
                raise ExecutionError(
                    message="Unknown execution error",
                    code=str(code),
                    details=details,
                    retryable=False,
                    raw=e,
                )

    import time
    import grpc
    def _now_msk(self):
        tz = pytz.timezone("Europe/Moscow")
        return datetime.now(tz)

    def _rpc_call(self, method, request, retries: int = 3):
        last_error = None

        for attempt in range(retries + 1):
            try:
                return method(request, metadata=self.metadata)

            except grpc.RpcError as e:
                last_error = e
                code = e.code()
                details = e.details() or ""

                print(f"[RPC ERROR] {code} | {details}")

                # 1️⃣ Техокно / недоступность
                if code in (
                        grpc.StatusCode.UNAVAILABLE,
                        grpc.StatusCode.INTERNAL,
                        grpc.StatusCode.DEADLINE_EXCEEDED,
                ):
                    print("⚠ Possible tech window. Backoff...")
                    time.sleep(2 * (attempt + 1))
                    continue

                # 2️⃣ JWT истёк
                if code == grpc.StatusCode.UNAUTHENTICATED:
                    print("🔄 Re-exchanging JWT token...")
                    self.jwt_token = self._exchange_token()
                    self.metadata = [("authorization", f"Bearer {self.jwt_token}")]
                    time.sleep(1)
                    continue

                # 3️⃣ Всё остальное — пробрасываем
                raise

            except Exception as e:
                last_error = e
                print(f"[GENERIC ERROR] {e}")
                time.sleep(1)

        raise last_error
    # -----------------------------
    # PUBLIC API
    # -----------------------------
    def is_tech_window(self) -> bool:
        return self._tech_window

    def get_trades(self, limit: int = 100):
        resp = self.get_trades_raw(limit=limit)
        trades = self.normalize_trades(resp)

        for t in trades:
            schema.validate_row(t, schema.TRADE_FIELDS, "TRADE")

        return trades

    def get_transactions(self, days: int = 7, limit: int = 100):
        resp = self.get_transactions_raw(days=days, limit=limit)
        tx = self.normalize_transactions(resp)

        for t in tx:
            schema.validate_row(t, schema.TRANSACTION_FIELDS, "TRANSACTION")

        return tx

    def get_account(self):
        req = accounts_service_pb2.GetAccountRequest(
            account_id=str(self.account_id)
        )
        return self._rpc_call(self.accounts.GetAccount, req)

    def get_portfolios_raw(self):
        account = self.get_account()

        balance = 0.0

        if getattr(account, "portfolio_mc", None) and account.portfolio_mc.available_cash:
            balance = float(account.portfolio_mc.available_cash.value)

        elif getattr(account, "portfolio_forts", None) and account.portfolio_forts.available_cash:
            balance = float(account.portfolio_forts.available_cash.value)

        return {
            "portfolios": [
                {
                    "account_id": account.account_id,
                    "balance": balance,
                }
            ]
        }
    def health_check(self) -> bool:
        try:
            self.get_account()
            return True
        except Exception:
            return False
    # -------------------------------------------------
    # TRADES
    # -------------------------------------------------
    def get_trades_raw(self, limit: int = 100, days: int = 7):
        from finam_bot.grpc_api.grpc.tradeapi.v1.accounts import accounts_service_pb2
        from google.type import interval_pb2
        from google.protobuf import timestamp_pb2
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        start = now - timedelta(days=int(days))

        interval = interval_pb2.Interval(
            start_time=timestamp_pb2.Timestamp(seconds=int(start.timestamp())),
            end_time=timestamp_pb2.Timestamp(seconds=int(now.timestamp())),
        )

        req = accounts_service_pb2.TradesRequest(
            account_id=str(self.account_id),
            limit=int(limit),
            interval=interval,
        )

        return self._rpc_call(self.accounts.Trades, req)
    # -------------------------------------------------
    # TRANSACTIONS
    # -------------------------------------------------
    def get_transactions_raw(self, days: int = 7, limit: int = 100):
        from finam_bot.grpc_api.grpc.tradeapi.v1.accounts import accounts_service_pb2
        from google.type import interval_pb2
        from google.protobuf import timestamp_pb2
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        start = now - timedelta(days=int(days))

        interval = interval_pb2.Interval(
            start_time=timestamp_pb2.Timestamp(seconds=int(start.timestamp())),
            end_time=timestamp_pb2.Timestamp(seconds=int(now.timestamp())),
        )

        req = accounts_service_pb2.TransactionsRequest(
            account_id=str(self.account_id),
            limit=int(limit),
            interval=interval,
        )

        return self._rpc_call(self.accounts.Transactions, req)

    def normalize_transactions(self, resp):
        out = []
        def _money_to_float(m) -> float:
            if m is None:
                return 0.0

            v = getattr(m, "value", None)
            if v not in (None, ""):
                return float(v)

            units = getattr(m, "units", None)
            nanos = getattr(m, "nanos", None)
            if units is not None or nanos is not None:
                u = int(units or 0)
                n = int(nanos or 0)
                return u + (n / 1_000_000_000)

            return 0.0

        def _money_currency(m) -> str:
            if m is None:
                return ""
            return getattr(m, "currency_code", "") or ""
        for t in resp.transactions:
            change = getattr(t, "change", None)

            out.append({
                "id": t.id,
                "ts": self._ts_to_iso(t.timestamp),
                "symbol": "",
                "category": t.category,
                "amount": _money_to_float(getattr(t, "change", None)),
                "currency": _money_currency(getattr(t, "change", None)),
                "description": getattr(t, "transaction_name", "") or "",
            })
            return out
    def _build_order(
            self,
            symbol: str,
            side: str,
            qty: float,
            order_type,
            price: float | None = None,
    ):
        from finam_bot.grpc_api.grpc.tradeapi.v1.orders import orders_service_pb2
        from finam_bot.grpc_api.grpc.tradeapi.v1 import side_pb2

        # если символ содержит @ — убираем суффикс
        base_symbol = symbol.split("@")[0]

        side_enum = (
            side_pb2.SIDE_BUY
            if side.upper() == "BUY"
            else side_pb2.SIDE_SELL
        )

        order = orders_service_pb2.Order(
            account_id=str(self.account_id),
            symbol=base_symbol,
            quantity=self._build_decimal(qty),
            side=side_enum,
            type=order_type,
        )

        if price is not None:
            order.limit_price.CopyFrom(self._build_decimal(price))

        return order
    # -------------------------------------------------
    # ORDERS
    # -------------------------------------------------

    def get_orders(self):
        req = orders_service_pb2.OrdersRequest(
            account_id=str(self.account_id)
        )
        return self._rpc_call(self.orders.GetOrders, req)

    def get_order(self, order_id: str):
        req = orders_service_pb2.GetOrderRequest(
            account_id=str(self.account_id),
            order_id=str(order_id),
        )
        return self._rpc_call(self.orders.GetOrder, req)

    def cancel_order(self, order_id: str):
        req = orders_service_pb2.CancelOrderRequest(
            account_id=str(self.account_id),
            order_id=str(order_id),
        )

        return self._rpc_call_exec(self.orders.CancelOrder, req, retries=1)
    # -------------------------------------------------
    # SYMBOL / MIC HELPERS
    # -------------------------------------------------

    def _parse_symbol(self, symbol: str) -> tuple[str, str]:
        """
        Принимает 'SBER@MISX'
        Возвращает ('SBER', 'MISX')
        """
        if "@" not in symbol:
            raise ValueError(
                "Symbol must include MIC suffix, e.g. SBER@MISX or BRH6@RTSX"
            )

        base, mic = symbol.split("@", 1)

        if not mic:
            raise ValueError("MIC part is empty")

        return base, mic

    def _build_decimal(self, value: float):
        from google.type import decimal_pb2
        return decimal_pb2.Decimal(value=str(value))
    # -------------------------------------------------
    # ORDERS
    # -------------------------------------------------

    def place_market_order(self, symbol: str, side: str, qty: float, mic: str):
        from finam_bot.grpc_api.grpc.tradeapi.v1.orders import orders_service_pb2
        from finam_bot.grpc_api.grpc.tradeapi.v1 import side_pb2

        side_enum = side_pb2.SIDE_BUY if side.upper() == "BUY" else side_pb2.SIDE_SELL

        symbol_full = self._join_symbol_mic(symbol, mic)

        order = orders_service_pb2.Order(
            account_id=str(self.account_id),
            symbol=symbol_full,
            quantity=self._build_decimal(qty),
            side=side_enum,
            type=orders_service_pb2.ORDER_TYPE_MARKET,
        )
        return self._rpc_call_exec(self.orders.PlaceOrder, order, retries=0)

    def place_limit_order(
            self,
            symbol: str,
            side: str,
            qty: float,
            price: float,
            mic: str,
    ):
        from finam_bot.grpc_api.grpc.tradeapi.v1.orders import orders_service_pb2
        from finam_bot.grpc_api.grpc.tradeapi.v1 import side_pb2
        from google.type import decimal_pb2

        symbol = self._join_symbol_mic(symbol, mic)

        side_enum = (
            side_pb2.SIDE_BUY
            if side.upper() == "BUY"
            else side_pb2.SIDE_SELL
        )

        order = orders_service_pb2.Order(
            account_id=str(self.account_id),
            symbol=str(symbol),
            quantity=decimal_pb2.Decimal(value=str(qty)),
            side=side_enum,
            type=orders_service_pb2.ORDER_TYPE_LIMIT,
            limit_price=decimal_pb2.Decimal(value=str(price)),
        )

        return self._rpc_call_exec(self.orders.PlaceOrder, order, retries=0)
    def normalize_trades(self, resp):
        def _money_to_float(m) -> float:
            """
            Поддержка разных вариантов представления суммы:
            - Decimal(value="...")  -> m.value
            - Money(units=..., nanos=...) -> units + nanos/1e9
            """
            if m is None:
                return 0.0

            # google.type.Decimal
            v = getattr(m, "value", None)
            if v not in (None, ""):
                return float(v)

            # protobuf money-like: units/nanos
            units = getattr(m, "units", None)
            nanos = getattr(m, "nanos", None)
            if units is not None or nanos is not None:
                u = int(units or 0)
                n = int(nanos or 0)
                return u + (n / 1_000_000_000)

            return 0.0

        def _money_currency(m) -> str:
            if m is None:
                return ""
            return getattr(m, "currency_code", "") or ""
        if not resp or not getattr(resp, "trades", None):
            return []

        result = []

        for t in resp.trades:
            sym, mic = self._split_symbol(t.symbol)

            result.append({
                "trade_id": t.trade_id,
                "account_id": t.account_id,
                "ts": self._ts_to_iso(t.timestamp),
                "symbol": sym,
                "mic": mic,
                "side": self._side_to_str(t.side),
                "qty": self._decimal_to_float(getattr(t, "size", None)),
                "price": self._decimal_to_float(getattr(t, "price", None)),                "order_id": t.order_id,
            })
        return result

    from datetime import datetime, timezone

    def _ts_to_iso(self, ts):
        if not ts:
            return None
        return datetime.fromtimestamp(
            ts.seconds + getattr(ts, "nanos", 0) / 1_000_000_000,
            tz=timezone.utc
        ).isoformat()

    def _join_symbol_mic(self, symbol: str, mic: str | None) -> str:
        s = (symbol or "").strip()
        if not s:
            raise ValueError("symbol must not be empty")

        # Если уже передали как 'BRH6@RTSX' — не трогаем
        if "@" in s:
            return s

        m = (mic or "").strip()
        if not m:
            raise ValueError("mic must not be empty (use e.g. RTSX/MISX)")
        return f"{s}@{m}"
    def _side_to_str(self, side):
        # REAL: enum Side (обычно 1/2), TEST может отдавать строки
        if side in (1, "SIDE_BUY", "BUY"):
            return "BUY"
        if side in (2, "SIDE_SELL", "SELL"):
            return "SELL"
        return ""

    def _split_symbol(self, symbol: str):
        if not symbol:
            return "", ""
        if "@" in symbol:
            s, mic = symbol.split("@", 1)
            return s, mic
        return symbol, ""

    def _decimal_to_float(self, d):
        if d is None:
            return 0.0

        v = getattr(d, "value", None)
        if v not in (None, ""):
            return float(v)

        units = getattr(d, "units", None)
        nanos = getattr(d, "nanos", None)

        if units is not None or nanos is not None:
            u = int(units or 0)
            n = int(nanos or 0)
            return u + (n / 1_000_000_000)

        return 0.0

    def get_positions(self):
        account = self.get_account()

        positions = []

        for p in getattr(account, "positions", []):
            raw_symbol = p.symbol or ""

            # Разделяем symbol и mic
            if "@" in raw_symbol:
                symbol, mic = raw_symbol.split("@", 1)
            else:
                symbol, mic = raw_symbol, ""

            qty = float(getattr(getattr(p, "quantity", None), "value", 0.0))
            avg_price = float(getattr(getattr(p, "average_price", None), "value", 0.0))
            current_price = float(getattr(getattr(p, "current_price", None), "value", 0.0))

            # PnL по позиции (если есть)
            unrealized = float(
                getattr(getattr(p, "unrealized_profit", None), "value", 0.0)
            )

            # если API не отдаёт unrealized по позиции — считаем вручную
            if unrealized == 0.0 and qty and current_price and avg_price:
                unrealized = (current_price - avg_price) * qty

            positions.append({
                "account_id": account.account_id,
                "symbol": symbol,
                "mic": mic,
                "qty": qty,
                "avg_price": avg_price,
                "current_price": current_price,
                "unrealized_pnl": unrealized,
            })

        return positions

    def get_positions(self):
        """
        Нормализованные позиции под schema.POSITION_FIELDS:
        account_id, symbol, mic, qty, avg_price, current_price, unrealized_pnl
        """
        account = self.get_account()

        positions = getattr(account, "positions", None) or []
        out = []

        for p in positions:
            sym_raw = getattr(p, "symbol", "") or ""
            symbol, mic = self._split_symbol_mic(sym_raw)

            qty = float(getattr(getattr(p, "quantity", None), "value", 0.0) or 0.0)
            avg_price = float(getattr(getattr(p, "average_price", None), "value", 0.0) or 0.0)

            # current_price в аккаунте обычно не приходит; берём last/close из marketdata при необходимости
            # Пока безопасно: 0.0
            current_price = float(getattr(getattr(p, "current_price", None), "value", 0.0) or 0.0)

            # unrealized_pnl в аккаунте может быть только агрегатным; на позицию часто нет
            unrealized_pnl = float(getattr(getattr(p, "unrealized_profit", None), "value", 0.0) or 0.0)

            out.append({
                "account_id": getattr(account, "account_id", ""),
                "symbol": symbol,
                "mic": mic,
                "qty": qty,
                "avg_price": avg_price,
                "current_price": current_price,
                "unrealized_pnl": unrealized_pnl,
            })

        return out

    def _split_symbol_mic(self, s: str):
        if not s:
            return "", ""
        if "@" in s:
            a, b = s.split("@", 1)
            return a, b
        return s, ""

    def place_oco(self, symbol, mic, side, qty, tp_price, sl_price):
        # TP
        tp = self.place_limit_order(symbol, side, qty, tp_price, mic)

        # SL (если API не поддерживает stop — делаем stop-limit)
        sl = self.place_limit_order(symbol, side, qty, sl_price, mic)

        return tp.order_id, sl.order_id

    from datetime import datetime, time as dt_time
    def _now_msk(self):
        from datetime import datetime, timezone, timedelta
        msk = timezone(timedelta(hours=3))
        return datetime.now(msk)

    def is_exchange_open(self) -> bool:
        """
        Простая проверка торговых часов MOEX.
        (Без учета вечерки, пока базовая версия)
        """

        now = datetime.now()

        # выходные
        if now.weekday() >= 5:
            return False

        current_time = now.time()

        market_open = dt_time(7, 0)
        market_close = dt_time(23, 50)

        return market_open <= current_time <= market_close
