#!/usr/bin/env python3

from __future__ import annotations

import os
import time
import grpc

from finam_proto.grpc.tradeapi.v1.marketdata import (
    marketdata_service_pb2,
    marketdata_service_pb2_grpc,
)

SYMBOL = os.environ.get("SYMBOL", "SBER@MISX")
GRPC_ENDPOINT = os.environ.get("FINAM_GRPC_ENDPOINT", "trade-api.finam.ru:443")
TOKEN = os.environ.get("FINAM_TOKEN") or os.environ.get("FINAM_ACCESS_TOKEN")
STREAM_SECONDS = float(os.environ.get("STREAM_SECONDS", "10"))


def decimal_to_float(value) -> float | None:
    if value is None:
        return None
    if hasattr(value, "units") and hasattr(value, "nanos"):
        return float(value.units) + float(value.nanos) / 1_000_000_000
    try:
        return float(str(value))
    except Exception:
        return None


def metadata():
    if not TOKEN:
        raise SystemExit("FINAM_TOKEN_NOT_SET")
    return (("authorization", f"Bearer {TOKEN}"),)


def print_trade(prefix: str, trade) -> None:
    price = decimal_to_float(trade.price)
    size = decimal_to_float(trade.size)

    print(
        f"{prefix} "
        f"trade_id={getattr(trade, 'trade_id', '')} "
        f"price={price} "
        f"size={size} "
        f"side={getattr(trade, 'side', '')}"
    )


def main() -> None:
    print("=== LIVE TRADE TAPE PROBE V1 ===")
    print(f"symbol={SYMBOL}")
    print(f"endpoint={GRPC_ENDPOINT}")
    print(f"stream_seconds={STREAM_SECONDS}")
    print()

    channel = grpc.secure_channel(GRPC_ENDPOINT, grpc.ssl_channel_credentials())
    stub = marketdata_service_pb2_grpc.MarketDataServiceStub(channel)

    started = time.perf_counter()

    try:
        req = marketdata_service_pb2.LatestTradesRequest(symbol=SYMBOL)
        resp = stub.LatestTrades(req, metadata=metadata(), timeout=10)

        latency_ms = (time.perf_counter() - started) * 1000
        trades = list(resp.trades)

        print("SNAPSHOT")
        print(f"snapshot_latency_ms={latency_ms:.2f}")
        print(f"trades={len(trades)}")

        for trade in trades[:10]:
            print_trade("snapshot_trade", trade)

    except Exception as exc:
        print(f"LATEST_TRADES_SNAPSHOT_ERROR={type(exc).__name__}: {exc}")

    print()
    print("STREAM")

    updates = 0
    trades_total = 0
    stream_started = time.perf_counter()

    try:
        req = marketdata_service_pb2.SubscribeLatestTradesRequest(symbol=SYMBOL)
        call = stub.SubscribeLatestTrades(req, metadata=metadata())

        for msg in call:
            updates += 1
            trades = list(msg.trades)
            trades_total += len(trades)

            print(f"stream_update={updates} trades={len(trades)}")

            for trade in trades[:5]:
                print_trade("stream_trade", trade)

            if time.perf_counter() - stream_started >= STREAM_SECONDS:
                call.cancel()
                break

    except Exception as exc:
        print(f"LATEST_TRADES_STREAM_ERROR={type(exc).__name__}: {exc}")

    elapsed = time.perf_counter() - stream_started
    updates_per_sec = updates / elapsed if elapsed > 0 else 0.0
    trades_per_sec = trades_total / elapsed if elapsed > 0 else 0.0

    print()
    print("RESULT")
    print(f"stream_updates={updates}")
    print(f"stream_trades={trades_total}")
    print(f"updates_per_sec={updates_per_sec:.4f}")
    print(f"trades_per_sec={trades_per_sec:.4f}")

    if updates > 0 or trades_total > 0:
        print("verdict=TRADE_TAPE_LIVE_CONFIRMED")
    else:
        print("verdict=TRADE_TAPE_NOT_CONFIRMED")


if __name__ == "__main__":
    main()
