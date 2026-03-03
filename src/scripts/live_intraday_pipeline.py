# src/scripts/live_intraday_pipeline.py
from __future__ import annotations

import os
import time
import signal
import traceback
from dataclasses import dataclass
from typing import Optional, Iterable

import grpc

# === FINAM PROTO (путь как у тебя) ===
from finam_proto.grpc.tradeapi.v1.marketdata import (
    marketdata_service_pb2_grpc as md_grpc,
    marketdata_service_pb2 as md_pb2,
)

# === твои модули ===
from core.position_manager import PositionManager


# -----------------------------
# Config
# -----------------------------

@dataclass(frozen=True)
class LiveConfig:
    host: str
    jwt: str
    symbol: str          # например "SBER@MISX"
    timeframe: str       # "M5" (как строка; маппинг ниже)
    reconnect_sec: int = 3
    heartbeat_sec: int = 20


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v if v not in (None, "") else default


def load_config() -> LiveConfig:
    host = _env("FINAM_GRPC_HOST") or _env("FINAM_API_HOST") or "api.finam.ru:443"

    # ВАЖНО: у тебя токен лежит в FINAM_TOKEN
    jwt = _env("FINAM_JWT") or _env("JWT") or _env("FINAM_TOKEN") or ""
    if not jwt:
        raise RuntimeError("Set FINAM_TOKEN (or FINAM_JWT / JWT) in .env")

    symbol = _env("SYMBOL") or "SBER@MISX"
    timeframe = _env("TIMEFRAME") or "M5"

    return LiveConfig(
        host=host,
        jwt=jwt,
        symbol=symbol,
        timeframe=timeframe,
    )


# -----------------------------
# Minimal Risk + Paper Exec
# -----------------------------

class RiskGuard:
    """Минимальный intraday-guard: запрет на сделки если qty слишком большой."""
    def __init__(self, max_abs_qty: float = 100.0):
        self.max_abs_qty = float(max_abs_qty)

    def allow(self, current_qty: float, side: str, qty: float) -> bool:
        target = current_qty + qty if side == "BUY" else current_qty - qty
        return abs(target) <= self.max_abs_qty


class PaperExecutor:
    """Исполнение 'по рынку' по цене close бара."""
    def execute(self, side: str, qty: float, price: float) -> dict:
        return {"side": side, "qty": qty, "price": price, "ts": time.time()}


# -----------------------------
# Strategy interface
# -----------------------------

@dataclass(frozen=True)
class Signal:
    side: str   # "BUY"|"SELL"
    qty: float


class Strategy:
    def on_bar(self, bar) -> Optional[Signal]:
        raise NotImplementedError


class SimpleMomentumStrategy(Strategy):
    """
    Простейшая: если close > open => BUY, иначе SELL.
    Это заглушка, чтобы pipeline был "живой".
    """
    def __init__(self, qty: float = 1.0):
        self.qty = float(qty)

    def on_bar(self, bar) -> Optional[Signal]:
        try:
            o = float(bar.open.value)
            c = float(bar.close.value)
        except Exception:
            return None
        if c > o:
            return Signal("BUY", self.qty)
        if c < o:
            return Signal("SELL", self.qty)
        return None


# -----------------------------
# MarketData: SubscribeBars
# -----------------------------

_TIMEFRAME_MAP = {
    # подстрой под enum если у тебя он отличается
    "M1": getattr(md_pb2, "Timeframe", None).TIMEFRAME_M1 if hasattr(md_pb2, "Timeframe") else 1,
    "M5": getattr(md_pb2, "Timeframe", None).TIMEFRAME_M5 if hasattr(md_pb2, "Timeframe") else 5,
    "M15": getattr(md_pb2, "Timeframe", None).TIMEFRAME_M15 if hasattr(md_pb2, "Timeframe") else 15,
    "H1": getattr(md_pb2, "Timeframe", None).TIMEFRAME_H1 if hasattr(md_pb2, "Timeframe") else 60,
}


class LiveBarsClient:
    def __init__(self, host: str, jwt: str):
        self.host = host
        self.jwt = jwt
        self.metadata = [("authorization", jwt)]
        self.channel = grpc.secure_channel(host, grpc.ssl_channel_credentials())
        self.stub = md_grpc.MarketDataServiceStub(self.channel)

    def subscribe_bars(self, symbol: str, timeframe: str):
        tf = _TIMEFRAME_MAP.get(timeframe.upper())
        if tf is None:
            raise ValueError(f"Unsupported TIMEFRAME={timeframe}. Use one of {sorted(_TIMEFRAME_MAP)}")

        # ВАЖНО: у Finam gRPC часто ожидание, что symbol уже включает MIC: "SBER@MISX"
        req = md_pb2.SubscribeBarsRequest(symbol=symbol, timeframe=tf)

        return self.stub.SubscribeBars(req, metadata=self.metadata)


# -----------------------------
# Pipeline runner
# -----------------------------

_STOP = False


def _handle_sigint(signum, frame):
    global _STOP
    _STOP = True


def run():
    cfg = load_config()
    signal.signal(signal.SIGINT, _handle_sigint)
    signal.signal(signal.SIGTERM, _handle_sigint)

    print("=== LIVE INTRADAY PIPELINE ===")
    print(f"Host: {cfg.host}")
    print(f"Symbol: {cfg.symbol}")
    print(f"Timeframe: {cfg.timeframe}")
    print("Ctrl+C to stop.\n")

    md = LiveBarsClient(cfg.host, cfg.jwt)
    strat: Strategy = SimpleMomentumStrategy(qty=float(_env("ORDER_QTY", "1")))
    risk = RiskGuard(max_abs_qty=float(_env("MAX_ABS_QTY", "50")))
    exe = PaperExecutor()
    pm = PositionManager()

    last_heartbeat = time.time()

    while not _STOP:
        try:
            stream = md.subscribe_bars(cfg.symbol, cfg.timeframe)
            print("SUBSCRIBED. Waiting for bars...")

            for msg in stream:
                if _STOP:
                    break

                # Heartbeat (если поток молчит)
                if time.time() - last_heartbeat >= cfg.heartbeat_sec:
                    print("HEARTBEAT: alive")
                    last_heartbeat = time.time()

                # Сообщения могут быть: bar или error
                if hasattr(msg, "error") and msg.error.code != 0:
                    print(f"EVENT ERROR: code={msg.error.code} desc={msg.error.description}")
                    continue

                if not hasattr(msg, "bar"):
                    print("EVENT: (unknown payload)", msg)
                    continue

                bar = msg.bar
                # Лог ключевых полей
                try:
                    c = float(bar.close.value)
                except Exception:
                    c = None
                print(f"BAR: ts={bar.timestamp.seconds}.{bar.timestamp.nanos} close={c}")

                sig = strat.on_bar(bar)
                if not sig:
                    continue

                if not risk.allow(pm.qty, sig.side, sig.qty):
                    print(f"RISK: blocked {sig.side} qty={sig.qty} (pos={pm.qty})")
                    continue

                if c is None:
                    print("EXEC: skipped (no close price)")
                    continue

                fill = exe.execute(sig.side, sig.qty, c)
                pm.on_fill(fill["side"], fill["qty"], fill["price"])
                snap = pm.snapshot(c)

                print(f"FILL: {fill} | SNAP: {snap}")

        except grpc.RpcError as e:
            # gRPC drop/reconnect
            print("STREAM ERROR:", repr(e))
            try:
                code = e.code()
                details = e.details()
                print(f"gRPC: code={code} details={details}")
            except Exception:
                pass

            if _STOP:
                break

            print(f"Reconnecting in {cfg.reconnect_sec}s...\n")
            time.sleep(cfg.reconnect_sec)

        except Exception:
            print("FATAL ERROR:\n", traceback.format_exc())
            if _STOP:
                break
            print(f"Restart loop in {cfg.reconnect_sec}s...\n")
            time.sleep(cfg.reconnect_sec)

    print("\nStopped.")


if __name__ == "__main__":
    run()