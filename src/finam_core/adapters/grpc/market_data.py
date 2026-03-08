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

        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self._active_call = None
        self._watchdog_thread: Optional[threading.Thread] = None
        self._last_watchdog_log_ts = 0.0

        self.tm = FinamTokenManager()

        # Русский коммент: канал/стаб переиспользуем, reconnect делаем на уровне stream call.
        self.channel = grpc.secure_channel(self.host, grpc.ssl_channel_credentials())
        self.stub = marketdata_service_pb2_grpc.MarketDataServiceStub(self.channel)

    # -----------------------------
    # Lifecycle
    # -----------------------------
    def start(self, symbols: List[str]):
        if self._thread and self._thread.is_alive():
            return
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
                    if now - self._last_watchdog_log_ts >= self.heartbeat_sec:
                        self._last_watchdog_log_ts = now
                        LOG.warning("MarketData heartbeat timeout — no ticks (soft watchdog). idle=%.1fs", idle)
                    continue

                # hard
                LOG.warning("MarketData heartbeat timeout — cancelling stream (hard watchdog). idle=%.1fs", idle)
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
        backoff = 0.5
        while not self._stop.is_set():
            try:
                req = marketdata_service_pb2.SubscribeQuoteRequest(symbols=symbols)
                call = self.stub.SubscribeQuote(req, metadata=self._md())

                self._active_call = call
                now = time.time()
                self.last_msg_ts = now
                self._subscribed_ts = now
                self._got_first_valid_quote = False
                self._last_watchdog_log_ts = 0.0

                self._start_watchdog()

                if os.getenv("MD_DEBUG") == "1":
                    LOG.debug("MarketData subscribed: %s", symbols)

                backoff = 0.5
                self._handle_stream(call)

            except grpc.RpcError as e:
                if self._stop.is_set():
                    break
                # Русский коммент: CANCELLED ожидаем в режиме hard, когда watchdog отменяет call.
                if os.getenv("MD_DEBUG") == "1":
                    LOG.debug("MarketData reconnect: %s", e)
                time.sleep(backoff)
                backoff = min(backoff * 2, 10.0)

            except Exception as e:
                if self._stop.is_set():
                    break
                LOG.exception("MarketData fatal (will reconnect): %s", e)
                time.sleep(backoff)
                backoff = min(backoff * 2, 10.0)

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
            if self._stop.is_set():
                return

            # Русский коммент: любое сообщение сбрасывает heartbeat (даже "пустое").
            self.last_msg_ts = time.time()

            quotes = self._iter_quotes(msg)
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
                }

                if os.getenv("MD_DEBUG") == "1":
                    LOG.debug("MD->BUS QUOTE %s last=%s", symbol, event.get("last"))

                self.event_bus.publish(event)
