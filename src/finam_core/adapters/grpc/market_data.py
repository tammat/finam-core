# -*- coding: utf-8 -*-
"""
Finam MarketData gRPC client -> EventBus

Инварианты:
- EventBus ожидает publish(event_dict) где event_dict["type"] определяет topic.
- subscribe(event_type, handler) где handler(event_dict)

Русские комментарии: объясняют критичные места (heartbeat/reconnect/stop).

Режимы watchdog:
- MD_WATCHDOG_MODE=soft (по умолчанию): НЕ рвём стрим, только пишем предупреждение раз в timeout.
- MD_WATCHDOG_MODE=hard: отменяем стрим и делаем reconnect.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Dict, Iterable, List, Optional

import grpc

from finam_core.auth.token_manager import FinamTokenManager
from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2
from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2_grpc

LOG = logging.getLogger(__name__)


class FinamMarketDataClient:
    """Quotes stream -> EventBus(QUOTE)."""

    def __init__(
        self,
        event_bus,
        *,
        host: str = "api.finam.ru:443",
        heartbeat_sec: float = 10.0,
    ):
        self.event_bus = event_bus
        self.host = host
        self.heartbeat_sec = float(heartbeat_sec)

        # Русский коммент: grace до первого валидного тика.
        self.first_quote_grace_sec = float(os.getenv("MD_FIRST_QUOTE_GRACE_SEC", "60"))
        self._subscribed_ts = 0.0
        self._got_first_valid_quote = False

        # Русский коммент: soft/hard watchdog.
        self.watchdog_mode = (os.getenv("MD_WATCHDOG_MODE") or "soft").strip().lower()
        if self.watchdog_mode not in ("soft", "hard"):
            self.watchdog_mode = "soft"

        self.state: Dict[str, Dict[str, Any]] = {}
        self.last_msg_ts = time.time()
        # Русский коммент: анти-спам для watchdog
        self._wd_last_warn_ts = 0.0
        self._wd_warn_every_sec = float(os.getenv("MD_WATCHDOG_WARN_EVERY_SEC", "3600"))  # 1 час


        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self._active_call = None
        self._debug_msg_count = 0
        self._watchdog_thread: Optional[threading.Thread] = None

        # === FIX: simulation mode bypass ===
        if os.getenv("SIMULATE_MARKET", "0") == "1":
            print("SIMULATED MARKET DATA ENABLED (no token)", flush=True)
            self.tm = None
        else:
            self.tm = FinamTokenManager()

        # Русский коммент: параметры reconnect без правки кода.
        self.reconnect_initial_sec = float(os.getenv("MD_RECONNECT_INITIAL_SEC", "0.5"))
        self.reconnect_max_sec = float(os.getenv("MD_RECONNECT_MAX_SEC", "30.0"))

        # Русский коммент: канал/стаб переиспользуем, reconnect делаем на уровне stream call.
        # Русский коммент: keepalive для 24/7 — помогает не терять idle соединение (NAT/провайдер).
        # Можно переопределить через env при необходимости.
        ka_time_ms = int(os.getenv("MD_GRPC_KEEPALIVE_TIME_MS", "30000"))
        ka_timeout_ms = int(os.getenv("MD_GRPC_KEEPALIVE_TIMEOUT_MS", "10000"))

        opts = [
            ("grpc.keepalive_time_ms", ka_time_ms),
            ("grpc.keepalive_timeout_ms", ka_timeout_ms),
            ("grpc.keepalive_permit_without_calls", 1),
            # Русский коммент: разрешаем ping без данных (иначе idle stream может рваться).
            ("grpc.http2.max_pings_without_data", 0),
            ("grpc.http2.min_time_between_pings_ms", ka_time_ms),
            ("grpc.http2.min_ping_interval_without_data_ms", ka_time_ms),
        ]

        self.channel = grpc.secure_channel(
            self.host,
            grpc.ssl_channel_credentials(),
            options=opts,
        )
        self.stub = marketdata_service_pb2_grpc.MarketDataServiceStub(self.channel)

    # -----------------------------
    # Lifecycle
    # -----------------------------
    def start(self, symbols: List[str]):
        if self._thread and self._thread.is_alive():
            LOG.info("MarketData start skipped: thread already alive symbols=%s", symbols)
            return
        LOG.info(
            "MarketData start: host=%s symbols=%s heartbeat_sec=%s watchdog=%s",
            self.host,
            symbols,
            self.heartbeat_sec,
            self.watchdog_mode,
        )
        self._thread = threading.Thread(target=self.subscribe_quotes, args=(symbols,), daemon=True)
        self._thread.start()

    def stop(self):
        """Останавливаем поток + отменяем активный call."""
        self._stop.set()
        try:
            if self._active_call is not None:
                self._active_call.cancel()
        except Exception:
            pass
        try:
            self.channel.close()
        except Exception:
            pass

    # -----------------------------
    # Internal helpers
    # -----------------------------
    def _md(self):
        # === FIX: simulation mode — no auth metadata ===
        if self.tm is None:
            return []
        jwt = self.tm.get_token()
        return [("authorization", f"Bearer {jwt}")]

    @staticmethod
    def _dec(v):
        """Finam Decimal -> float (best-effort)."""
        try:
            if v is None:
                return None
            if hasattr(v, "value"):
                s = v.value
                if not s:
                    return None
                return float(s)
            return float(v)
        except Exception:
            return None

    def _start_watchdog(self):
        """Watchdog следит за отсутствием сообщений и действует по режиму (soft/hard)."""
        if self._watchdog_thread and self._watchdog_thread.is_alive():
            return

        def _wd():
            while not self._stop.is_set():
                time.sleep(0.5)
                if self._active_call is None:
                    continue

                now = time.time()

                # Русский коммент: пока не прошло grace и не было валидного тика — не предпринимаем действий.
                if (now - self._subscribed_ts) < self.first_quote_grace_sec and not self._got_first_valid_quote:
                    continue

                idle = now - self.last_msg_ts
                if idle <= self.heartbeat_sec:
                    continue

                # Русский коммент: soft — только предупреждение раз в heartbeat_sec, hard — cancel/reconnect.
                if self.watchdog_mode == "soft":
                    # Русский коммент: quiet-soft — по умолчанию молчим, чтобы не засорять логи в нерабочее время.
                    # Пишем предупреждение только при MD_DEBUG=1 и не чаще, чем раз в MD_WATCHDOG_WARN_EVERY_SEC.
                    if os.getenv("MD_DEBUG") == "1" and (now - self._wd_last_warn_ts) >= self._wd_warn_every_sec:
                        self._wd_last_warn_ts = now
                        LOG.warning(
                            "MarketData heartbeat timeout — no ticks (soft watchdog). idle=%.1fs",
                            idle,
                        )
                    continue

                # hard
                LOG.warning(
                    "MarketData heartbeat timeout — cancelling stream (hard watchdog). idle=%.1fs",
                    idle,
                )
                try:
                    self._active_call.cancel()
                except Exception:
                    pass
                return

        self._watchdog_thread = threading.Thread(target=_wd, daemon=True)
        self._watchdog_thread.start()

    # -----------------------------
    # Streaming loop
    # -----------------------------
    def subscribe_quotes(self, symbols: List[str]):
        # === FIX: full simulation mode — disable gRPC completely ===
        if self.tm is None:
            print("SIMULATION MODE ACTIVE — skipping Finam gRPC", flush=True)
            while not self._stop.is_set():
                time.sleep(1)
            return
        backoff = self.reconnect_initial_sec
        while not self._stop.is_set():
            try:
                req = marketdata_service_pb2.SubscribeQuoteRequest(symbols=symbols)
                call = self.stub.SubscribeQuote(req, metadata=self._md())

                self._active_call = call
                now = time.time()
                self.last_msg_ts = now
                self._subscribed_ts = now
                self._got_first_valid_quote = False

                self._start_watchdog()

                LOG.info("MarketData SubscribeQuote opened: symbols=%s", symbols)
                if os.getenv("MD_DEBUG") == "1":
                    LOG.debug("MarketData subscribed debug: %s", symbols)

                backoff = self.reconnect_initial_sec
                self._handle_stream(call)

            except grpc.RpcError as e:
                if self._stop.is_set():
                    break
                # Русский коммент: CANCELLED ожидаем в режиме hard, когда watchdog отменяет call.
                # Русский коммент: в soft режиме ошибки на тишине не должны появляться; если появились — это сеть/сервер.
                LOG.warning("MarketData reconnect after RpcError: %s", e)
                if os.getenv("MD_DEBUG") == "1":
                    LOG.debug("MarketData reconnect debug", exc_info=True)
                LOG.warning("MarketData reconnect in %.1fs", backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, self.reconnect_max_sec)

            except Exception as e:
                if self._stop.is_set():
                    break
                LOG.exception("MarketData fatal (will reconnect): %s", e)
                LOG.warning("MarketData reconnect in %.1fs", backoff)
                time.sleep(backoff)
                backoff = min(backoff * 2, self.reconnect_max_sec)

            finally:
                self._active_call = None

    def _iter_quotes(self, msg):
        """
        Русский коммент:
        gRPC может прислать:
        - msg.quote (один quote-объект)
        - msg.quote как repeated-контейнер
        - msg.quotes
        Возвращаем список quote-объектов.
        """
        q = getattr(msg, "quote", None)
        if q is not None:
            if hasattr(q, "symbol"):
                return [q]
            try:
                return list(q)
            except TypeError:
                pass

        qs = getattr(msg, "quotes", None)
        if qs is not None:
            try:
                return list(qs)
            except TypeError:
                pass

        return []

    def _handle_stream(self, stream: Iterable):
        """Чтение потока и публикация событий QUOTE в EventBus."""
        for msg in stream:
            if self._debug_msg_count < 3:
                self._debug_msg_count += 1
            if os.getenv("MD_DEBUG") == "1":
                LOG.debug("MarketData raw stream msg=%s", msg)
            if self._stop.is_set():
                return

            # Русский коммент: любое сообщение сбрасывает heartbeat (даже "пустое").
            self.last_msg_ts = time.time()

            quotes = self._iter_quotes(msg)
            if os.getenv("MD_DEBUG") == "1":
                LOG.debug("MarketData parsed quotes count=%s", len(quotes))
            if not quotes:
                continue

            for quote in quotes:
                symbol = getattr(quote, "symbol", None)
                if not symbol:
                    continue

                state = self.state.get(symbol, {})
                state["symbol"] = symbol

                # Русский коммент: частичные кадры — обновляем только пришедшие поля.
                for k in ("bid", "ask", "last", "volume", "open", "high", "low", "close"):
                    val = getattr(quote, k, None)
                    if val is not None:
                        state[k] = self._dec(val)

                self.state[symbol] = state

                # Русский коммент: считаем "валидным тиком" наличие symbol + last.
                if state.get("last") is not None:
                    self._got_first_valid_quote = True

                event = {
                    "type": "QUOTE",
                    "symbol": symbol,
                    "bid": state.get("bid"),
                    "ask": state.get("ask"),
                    "last": state.get("last"),
                    "volume": state.get("volume"),
                    # Русский коммент: OHLC нужны LiveFeatureBuffer и фильтрам режима.
                    "open": state.get("open"),
                    "high": state.get("high"),
                    "low": state.get("low"),
                    "close": state.get("close"),
                }

                if os.getenv("MD_DEBUG") == "1":
                    LOG.debug("MD->BUS QUOTE %s last=%s", symbol, event.get("last"))

                if os.getenv("MD_DEBUG") == "1":
                    LOG.debug("MarketData publish QUOTE event=%s", event)
                try:
                    self.event_bus.publish(event)
                except Exception as e:
                    LOG.exception("MarketData publish failed: %s", e)

# ---------------------------------------------------------------------
# Backward-compatible bars stream for legacy LiveMarketFeed
# ---------------------------------------------------------------------
from dataclasses import dataclass


@dataclass
class MarketBar:
    symbol: str
    close: float
    timestamp: float


def _subscribe_bars_compat(self, symbol: str, timeframe: int = 1):
    """
    Legacy-compatible adapter:
    LiveMarketFeed expects: for bar in client.subscribe_bars(symbol, 1)
    Internally we reuse quotes state populated by subscribe_quotes().
    """
    self.start([symbol])

    last_price = None

    while not self._stop.is_set():
        state = self.state.get(symbol) or {}
        price = state.get("price") or state.get("last") or state.get("close")

        if price is not None and price != last_price:
            last_price = price
            yield MarketBar(
                symbol=symbol,
                close=float(price),
                timestamp=float(state.get("timestamp") or time.time()),
            )

        time.sleep(float(os.getenv("MD_BAR_POLL_SEC", "0.5")))


FinamMarketDataClient.subscribe_bars = _subscribe_bars_compat
