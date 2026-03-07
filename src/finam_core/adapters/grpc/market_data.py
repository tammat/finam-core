import os
import grpc
import threading
import time
from typing import Any, Dict, Iterable, List, Optional

from finam_core.auth.token_manager import FinamTokenManager
from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2
from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2_grpc


class FinamMarketDataClient:
    """
    gRPC MarketData (quotes) -> EventBus.

    Ключевые фиксы:
    - JWT обновляем на КАЖДУЮ попытку Subscribe (иначе поток молчит после ротации токена)
    - heartbeat через watchdog + cancel() активного вызова (НЕ закрываем channel внутри потока)
    - stop() корректно останавливает поток и закрывает channel
    - msg.quote — одиночное поле, НЕ iterable
    """

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

        self.state: Dict[str, Dict[str, Any]] = {}
        self.last_msg_ts = time.time()

        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self._active_call = None
        self._watchdog: Optional[threading.Thread] = None

        self.tm = FinamTokenManager()
        self.channel = grpc.secure_channel(self.host, grpc.ssl_channel_credentials())
        self.stub = marketdata_service_pb2_grpc.MarketDataServiceStub(self.channel)

    # ----------------------------
    # lifecycle
    # ----------------------------
    def start(self, symbols: List[str]) -> None:
        # Комментарий: защищаемся от двойного старта
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self.subscribe_quotes,
            args=(symbols,),
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        # Комментарий: корректный stop — сначала cancel активного stream, потом close channel
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

    def _md(self):
        # Комментарий: JWT обновляем на КАЖДУЮ подписку
        jwt = self.tm.get_token()
        return [("authorization", f"Bearer {jwt}")]

    def _start_watchdog(self) -> None:
        # Комментарий: watchdog один, не плодим потоки
        if self._watchdog and self._watchdog.is_alive():
            return

        def _run():
            while not self._stop.is_set():
                time.sleep(0.5)
                call = self._active_call
                if call is None:
                    continue
                if (time.time() - self.last_msg_ts) > self.heartbeat_sec:
                    # Комментарий: важное — НЕ закрываем channel, только cancel stream
                    if os.getenv("MD_DEBUG") == "1":
                        print("MarketData heartbeat timeout — cancelling stream", flush=True)
                    try:
                        call.cancel()
                    except Exception:
                        pass
                    return

        self._watchdog = threading.Thread(target=_run, daemon=True)
        self._watchdog.start()

    # ----------------------------
    # subscribe loop
    # ----------------------------
    def subscribe_quotes(self, symbols: List[str]) -> None:
        backoff = 0.5
        while not self._stop.is_set():
            try:
                req = marketdata_service_pb2.SubscribeQuoteRequest(symbols=symbols)

                call = self.stub.SubscribeQuote(req, metadata=self._md())
                self._active_call = call
                self.last_msg_ts = time.time()
                self._start_watchdog()

                if os.getenv("MD_DEBUG") == "1":
                    print(f"MarketData subscribed: {symbols}", flush=True)

                backoff = 0.5
                self._handle_stream(call)

            except grpc.RpcError as e:
                if self._stop.is_set():
                    break
                # Комментарий: CANCELLED тут нормален (stop/watchdog)
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

    def _handle_stream(self, stream: Iterable) -> None:
        for msg in stream:
            if self._stop.is_set():
                return

            self.last_msg_ts = time.time()

            quote_field = getattr(msg, "quote", None)
            if quote_field is None:
                continue

            # Finam: msg.quote может быть либо одним сообщением, либо repeated (список)
            if hasattr(quote_field, "__len__") and not hasattr(quote_field, "symbol"):
                quotes = list(quote_field)
            else:
                quotes = [quote_field]

            for quote in quotes:
                symbol = getattr(quote, "symbol", None)
                if not symbol:
                    continue

                state = self.state.get(symbol, {})
                state["symbol"] = symbol

                def _dec(v):
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

                for k in ("bid", "ask", "last", "volume", "open", "high", "low", "close"):
                    val = getattr(quote, k, None)
                    if val is not None:
                        state[k] = _dec(val)

                self.state[symbol] = state

                event = {
                    "type": "QUOTE",
                    "symbol": symbol,
                    "bid": state.get("bid"),
                    "ask": state.get("ask"),
                    "last": state.get("last"),
                    "volume": state.get("volume"),
                }
                # DEBUG по желанию
                if os.getenv("MD_DEBUG") == "1":
                    print(f"MD->BUS QUOTE {symbol} last={event.get('last')}", flush=True)

                # ВАЖНО: отправляем в EventBus
                self.event_bus.publish(event)
                if os.getenv("MD_DEBUG") == "1":
                    print(f"MD->BUS QUOTE {symbol} last={event.get('last')}", flush=True)

                # Публикуем строго в topic "QUOTE" для EventBus(topic-based)
                try:
                    # Публикуем ОДИН объект события: EventBus сам маршрутизирует по event["type"]
                    self.event_bus.publish(event)
                except TypeError:
                    # fallback: если EventBus поддерживает publish(event) и сам берет event["type"]
                    self.event_bus.publish(event)
                if not symbol:
                    continue

            state = self.state.get(symbol, {})
            state["symbol"] = symbol

            def _dec(v):
                # Комментарий: google.type.Decimal (value: str) -> float
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

            for k in ("bid", "ask", "last", "volume", "open", "high", "low", "close"):
                val = getattr(quote, k, None)
                if val is not None:
                    state[k] = _dec(val)

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
