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


def row_side(row) -> str:
    if getattr(row, "buy_size", None):
        return "BUY"
    if getattr(row, "sell_size", None):
        return "SELL"
    return "UNKNOWN"


def main() -> None:
    print("=== LIVE ORDERBOOK PROBE V1 ===")
    print(f"symbol={SYMBOL}")
    print(f"endpoint={GRPC_ENDPOINT}")
    print(f"stream_seconds={STREAM_SECONDS}")
    print()

    channel = grpc.secure_channel(GRPC_ENDPOINT, grpc.ssl_channel_credentials())
    stub = marketdata_service_pb2_grpc.MarketDataServiceStub(channel)

    started = time.perf_counter()

    try:
        req = marketdata_service_pb2.OrderBookRequest(symbol=SYMBOL)
        resp = stub.OrderBook(req, metadata=metadata(), timeout=10)

        latency_ms = (time.perf_counter() - started) * 1000
        rows = list(resp.orderbook.rows)

        bids = []
        asks = []

        for row in rows:
            price = decimal_to_float(row.price)
            buy_size = decimal_to_float(row.buy_size)
            sell_size = decimal_to_float(row.sell_size)

            if price is None:
                continue

            if buy_size and buy_size > 0:
                bids.append((price, buy_size))

            if sell_size and sell_size > 0:
                asks.append((price, sell_size))

        best_bid = max([x[0] for x in bids], default=None)
        best_ask = min([x[0] for x in asks], default=None)

        spread = None
        spread_pct = None

        if best_bid and best_ask:
            spread = best_ask - best_bid
            spread_pct = spread / best_bid * 100

        print("SNAPSHOT")
        print(f"snapshot_latency_ms={latency_ms:.2f}")
        print(f"rows={len(rows)}")
        print(f"bid_levels={len(bids)}")
        print(f"ask_levels={len(asks)}")
        print(f"best_bid={best_bid}")
        print(f"best_ask={best_ask}")
        print(f"spread={spread}")
        print(f"spread_pct={spread_pct}")

    except Exception as exc:
        print(f"ORDERBOOK_SNAPSHOT_ERROR={type(exc).__name__}: {exc}")

    print()
    print("STREAM")

    updates = 0
    rows_total = 0
    stream_started = time.perf_counter()

    try:
        req = marketdata_service_pb2.SubscribeOrderBookRequest(symbol=SYMBOL)
        call = stub.SubscribeOrderBook(req, metadata=metadata())

        for msg in call:
            updates += 1

            batch_rows = 0
            for book in msg.order_book:
                batch_rows += len(book.rows)

            rows_total += batch_rows

            print(f"stream_update={updates} rows={batch_rows}")

            if time.perf_counter() - stream_started >= STREAM_SECONDS:
                call.cancel()
                break

    except Exception as exc:
        print(f"ORDERBOOK_STREAM_ERROR={type(exc).__name__}: {exc}")

    elapsed = time.perf_counter() - stream_started
    updates_per_sec = updates / elapsed if elapsed > 0 else 0.0

    print()
    print("RESULT")
    print(f"stream_updates={updates}")
    print(f"stream_rows={rows_total}")
    print(f"updates_per_sec={updates_per_sec:.4f}")

    if updates > 0:
        print("verdict=ORDERBOOK_LIVE_CONFIRMED")
    else:
        print("verdict=ORDERBOOK_NOT_CONFIRMED")


if __name__ == "__main__":
    main()
