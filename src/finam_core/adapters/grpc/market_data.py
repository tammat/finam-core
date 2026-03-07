# -*- coding: utf-8 -*-
"""
Finam MarketData gRPC client -> EventBus

Инварианты:
- EventBus ожидает publish(event_dict) где event_dict["type"] определяет topic.
- subscribe(event_type, handler) где handler(event_dict)

Русские комментарии: объясняют критичные места (heartbeat/reconnect/stop).
"""

import os
import time
import grpc
import threading
from typing import Iterable, Optional, List, Dict, Any

from finam_core.auth.token_manager import FinamTokenManager
from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2
from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2_grpc


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

        self.state: Dict[str, Dict[str, Any]] = {}  # symbol -> last snapshot (bid/ask/last/volume...)
        self.last_msg_ts = time.time()

        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # active gRPC call + watchdog
        self._active_call = None
        self._watchdog_thread: Optional[threading.Thread] = None

        self.tm = FinamTokenManager()

        # channel/stub (reused)
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
        """Watchdog отменяет stream если нет сообщений heartbeat_sec."""
        if self._watchdog_thread and self._watchdog_thread.is_alive():
            return

        def _wd():
            while not self._stop.is_set():
                time.sleep(0.5)
                if self._active_call is None:
                    continue
                if (time.time() - self.last_msg_ts) > self.heartbeat_sec:
                    # Русский коммент: это нормальная отмена — subscribe_quotes поймает CANCELLED и перезапустит
                    if os.getenv("MD_DEBUG") == "1":
                        print("MarketData heartbeat timeout — cancelling stream", flush=True)
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
                self.last_msg_ts = time.time()
                self._start_watchdog()

                print(f"MarketData subscribed: {symbols}", flush=True)
                backoff = 0.5

                self._handle_stream(call)

            except grpc.RpcError as e:
                if self._stop.is_set():
                    break
                if os.getenv("MD_DEBUG") == "1":
                    print(f"MarketData reconnect: {e}", flush=True)
                time.sleep(backoff)
                backoff = min(backoff * 2, 10.0)
            except Exception as e:
                if self._stop.is_set():
                    break
                print(f"MarketData fatal (will reconnect): {e}", flush=True)
                time.sleep(backoff)
                backoff = min(backoff * 2, 10.0)
            finally:
                self._active_call = None
    def _iter_quotes(self, msg):
        """
        Русский коммент: gRPC может прислать либо msg.quote (один объект),
        либо msg.quote как repeated-контейнер, либо msg.quotes.
        Возвращаем список quote-объектов.
        """
        q = getattr(msg, "quote", None)
        if q is not None:
            if hasattr(q, "symbol"):
                return [q]
            try:
                return list(q)  # repeated container
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
        for msg in stream:
            if self._stop.is_set():
                return

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

                for k in ("bid", "ask", "last", "volume", "open", "high", "low", "close"):
                    val = getattr(quote, k, None)
                    if val is not None:
                        state[k] = self._dec(val)

                self.state[symbol] = state

                event = {
                    "type": "QUOTE",
                    "symbol": symbol,
                    "bid": state.get("bid"),
                    "ask": state.get("ask"),
                    "last": state.get("last"),
                    "volume": state.get("volume"),
                }

                if os.getenv("MD_DEBUG") == "1":
                    print(f"MD->BUS QUOTE {symbol} last={event.get('last')}", flush=True)

                self.event_bus.publish(event)
                if not symbol:
                    continue

            state = self.state.get(symbol, {})
            state["symbol"] = symbol

            # Русский коммент: частичные кадры — обновляем только пришедшие поля
            for k in ("bid", "ask", "last", "volume", "open", "high", "low", "close"):
                val = getattr(quote, k, None)
                if val is not None:
                    state[k] = self._dec(val)

            self.state[symbol] = state

            event = {
                "type": "QUOTE",
                "symbol": symbol,
                "bid": state.get("bid"),
                "ask": state.get("ask"),
                "last": state.get("last"),
                "volume": state.get("volume"),
            }

            if os.getenv("MD_DEBUG") == "1":
                print(f"MD->BUS QUOTE {symbol} last={event.get('last')}", flush=True)

            # ВАЖНО: publish(event) — EventBus сам маршрутизирует по event["type"]
            self.event_bus.publish(event)

    def _iter_quotes(self, msg):
        """
        Русский коммент: gRPC может прислать либо msg.quote (один объект),
        либо msg.quote как repeated-контейнер, либо msg.quotes.
        Возвращаем список quote-объектов.
        """
        q = getattr(msg, "quote", None)
        if q is not None:
            if hasattr(q, "symbol"):
                return [q]
            try:
                return list(q)  # repeated container
            except TypeError:
                pass

        qs = getattr(msg, "quotes", None)
        if qs is not None:
            try:
                return list(qs)
            except TypeError:
                pass

        return []
