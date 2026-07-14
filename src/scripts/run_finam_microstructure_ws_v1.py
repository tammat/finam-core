from __future__ import annotations

import asyncio
import json
import os
import signal
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import psycopg2
import psycopg2.extras
import websockets

from finam_core.auth.token_manager import FinamTokenManager


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
WS_URL = os.getenv("FINAM_WS_URL", "wss://api.finam.ru/ws")
SYMBOLS = tuple(
    item.strip() for item in os.getenv(
        "MARKETCORE_MICROSTRUCTURE_SYMBOLS",
        "SBER@MISX,LKOH@MISX,GAZP@MISX,PLZL@MISX,USDRUBF@RTSX,BRQ6@RTSX,NGQ6@RTSX",
    ).split(",") if item.strip()
)
SOURCE = "FINAM_MICROSTRUCTURE_WS_V1"
DATA_STALE_AFTER_SEC = float(os.getenv("MARKETCORE_MICROSTRUCTURE_DATA_STALE_AFTER_SEC", "90"))
MAX_SYMBOLS = int(os.getenv("MARKETCORE_MICROSTRUCTURE_MAX_SYMBOLS", "64"))


class StaleDataError(RuntimeError):
    pass


def data_is_stale(last_persisted_at: float, now: float, threshold_seconds: float) -> bool:
    return now-last_persisted_at >= threshold_seconds


def finam_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper()
    if symbol in {"IMOEX", "IMOEX2", "RTSI"}:
        return f"{symbol}@MISX"
    return symbol


def merge_symbols(*groups: list[str] | tuple[str, ...], limit: int = MAX_SYMBOLS) -> tuple[str, ...]:
    symbols: list[str] = []
    for group in groups:
        for raw_symbol in group:
            symbol = finam_symbol(raw_symbol)
            if symbol and symbol not in symbols:
                symbols.append(symbol)
    return tuple(symbols[:limit])


def number(value: Any) -> Decimal | None:
    if value in (None, ""):
        return None
    if isinstance(value, dict):
        value = value.get("value") or value.get("units")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def timestamp(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def object_value(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def list_value(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


class Collector:
    def __init__(self) -> None:
        self.token_manager = FinamTokenManager()
        self.stop = asyncio.Event()
        self.books: dict[str, dict[str, dict[Decimal, Decimal]]] = {}
        self.last_saved: dict[str, float] = {}
        self.last_persisted_at = time.monotonic()
        self.conn = psycopg2.connect(DB)
        self.conn.autocommit = True

    def subscription_symbols(self) -> tuple[str, ...]:
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT symbol FROM public.market_data_watch_universe
                WHERE is_enabled ORDER BY symbol
            """)
            watched = [str(row[0]) for row in cur.fetchall()]
            cur.execute("""
                SELECT DISTINCT symbol
                FROM analytics.forward_edge_shadow_trade_v1
                WHERE cohort_id=(
                    SELECT cohort_id FROM analytics.forward_edge_shadow_trade_v1
                    ORDER BY created_at DESC LIMIT 1
                )
            """)
            shadow = [str(row[0]) for row in cur.fetchall()]
            cur.execute("""
                SELECT DISTINCT symbol FROM public.signal_fills
                WHERE created_at >= current_date-1
            """)
            recent_fills = [str(row[0]) for row in cur.fetchall()]
        return merge_symbols(SYMBOLS, watched, shadow, recent_fills)

    def close(self) -> None:
        self.token_manager.close()
        self.conn.close()

    async def subscribe(self, ws: Any, token: str, symbols: tuple[str, ...]) -> None:
        await ws.send(json.dumps({
            "action": "SUBSCRIBE", "type": "QUOTES",
            "data": {"symbols": list(symbols)}, "token": token,
        }))
        for symbol in symbols:
            for subscription_type in ("ORDER_BOOK", "INSTRUMENT_TRADES"):
                await ws.send(json.dumps({
                    "action": "SUBSCRIBE", "type": subscription_type,
                    "data": {"symbol": symbol}, "token": token,
                }))

    def insert_snapshot(
        self, symbol: str, exchange_ts: datetime | None,
        best_bid: Decimal, best_ask: Decimal,
        bid_size: Decimal | None, ask_size: Decimal | None,
        bid_depth: Decimal, ask_depth: Decimal,
        bid_levels: int, ask_levels: int, envelope: dict[str, Any],
    ) -> None:
        if best_bid <= 0 or best_ask <= 0:
            return
        spread = best_ask-best_bid
        spread_bps = spread/best_bid*Decimal(10000)
        total_depth = bid_depth+ask_depth
        imbalance = (bid_depth-ask_depth)/total_depth if total_depth else None
        observed = datetime.now(timezone.utc)
        latency_ms = Decimal(str((observed-exchange_ts).total_seconds()*1000)) if exchange_ts else None
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO analytics.market_microstructure_snapshot_v1
                (observed_at,exchange_ts,symbol,best_bid,best_ask,bid_size,ask_size,
                 spread,spread_bps,bid_depth,ask_depth,imbalance,bid_levels,ask_levels,
                 source_latency_ms,source_code,raw_json)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (observed,exchange_ts,symbol,best_bid,best_ask,bid_size,ask_size,
                 spread,spread_bps,bid_depth,ask_depth,imbalance,bid_levels,ask_levels,
                 latency_ms,SOURCE,psycopg2.extras.Json(envelope)),
            )
        self.last_persisted_at = time.monotonic()

    def save_quote(self, quote: dict[str, Any], envelope: dict[str, Any]) -> None:
        symbol = str(quote.get("symbol") or "")
        bid, ask = number(quote.get("bid")), number(quote.get("ask"))
        if not symbol or bid is None or ask is None:
            return
        bid_size, ask_size = number(quote.get("bid_size")), number(quote.get("ask_size"))
        self.insert_snapshot(
            symbol, timestamp(quote.get("timestamp")), bid, ask,
            bid_size, ask_size, bid_size or Decimal(0), ask_size or Decimal(0),
            1, 1, envelope,
        )

    def save_order_book(self, book: dict[str, Any], envelope: dict[str, Any]) -> None:
        symbol = str(book.get("symbol") or "")
        if not symbol:
            return
        state = self.books.setdefault(symbol, {"bid": {}, "ask": {}})
        exchange_ts = None
        for row in list_value(book.get("rows")):
            price = number(row.get("price"))
            if price is None:
                continue
            exchange_ts = timestamp(row.get("timestamp")) or exchange_ts
            action = str(row.get("action") or "")
            buy_size, sell_size = number(row.get("buy_size")), number(row.get("sell_size"))
            side = "bid" if buy_size is not None else "ask" if sell_size is not None else ""
            if not side:
                continue
            size = buy_size if side == "bid" else sell_size
            if action == "ACTION_REMOVE" or size is None or size <= 0:
                state[side].pop(price, None)
            else:
                state[side][price] = size
        now = time.monotonic()
        if now-self.last_saved.get(symbol, 0.0) < 1.0:
            return
        bids, asks = state["bid"], state["ask"]
        if not bids or not asks:
            return
        best_bid, best_ask = max(bids), min(asks)
        self.last_saved[symbol] = now
        self.insert_snapshot(
            symbol, exchange_ts, best_bid, best_ask,
            bids[best_bid], asks[best_ask], sum(bids.values()), sum(asks.values()),
            len(bids), len(asks), envelope,
        )

    def save_trades(self, payload: dict[str, Any], envelope: dict[str, Any]) -> None:
        symbol = str(payload.get("symbol") or "")
        if not symbol:
            return
        inserted = 0
        with self.conn.cursor() as cur:
            for trade in list_value(payload.get("trades")):
                trade_id = str(trade.get("trade_id") or "")
                ts = timestamp(trade.get("timestamp"))
                price, size = number(trade.get("price")), number(trade.get("size"))
                if not trade_id or ts is None or price is None or size is None:
                    continue
                cur.execute(
                    """
                    INSERT INTO analytics.market_trade_tape_v1
                    (symbol,trade_id,exchange_ts,price,size,side_code,mpid,source_code,raw_json)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(symbol,trade_id) DO NOTHING
                    """,
                    (symbol,trade_id,ts,price,size,str(trade.get("side") or "UNKNOWN"),
                     str(trade.get("mpid") or ""),SOURCE,psycopg2.extras.Json(envelope)),
                )
                inserted += max(cur.rowcount, 0)
        if inserted:
            self.last_persisted_at = time.monotonic()

    def process(self, envelope: dict[str, Any]) -> None:
        if envelope.get("type") != "DATA":
            if envelope.get("type") == "ERROR":
                print("ws_error="+json.dumps(envelope.get("error_info") or {},ensure_ascii=False),flush=True)
            return
        kind = str(envelope.get("subscription_type") or "")
        payload = object_value(envelope.get("payload"))
        if kind == "QUOTES":
            for quote in list_value(payload.get("quote")):
                self.save_quote(quote,envelope)
        elif kind == "ORDER_BOOK":
            for book in list_value(payload.get("order_book")):
                self.save_order_book(book,envelope)
        elif kind == "INSTRUMENT_TRADES":
            self.save_trades(payload,envelope)

    async def run(self) -> None:
        backoff = 2
        while not self.stop.is_set():
            try:
                token = self.token_manager.get_token()
                async with websockets.connect(
                    WS_URL, additional_headers={"Authorization": token},
                    ping_interval=20, ping_timeout=20, max_size=8_000_000,
                ) as ws:
                    symbols = self.subscription_symbols()
                    await self.subscribe(ws,token,symbols)
                    print(
                        f"status=CONNECTED symbols={len(symbols)} universe={','.join(symbols)}",
                        flush=True,
                    )
                    connected_at = time.monotonic()
                    self.last_persisted_at = connected_at
                    backoff = 2
                    while not self.stop.is_set() and time.monotonic()-connected_at < 540:
                        message = await asyncio.wait_for(ws.recv(),timeout=60)
                        envelope = json.loads(message)
                        self.process(object_value(envelope))
                        now = time.monotonic()
                        if data_is_stale(self.last_persisted_at, now, DATA_STALE_AFTER_SEC):
                            stale_for = now-self.last_persisted_at
                            raise StaleDataError(f"no_persisted_market_data_for={stale_for:.1f}s")
            except asyncio.TimeoutError:
                print("status=RECONNECT reason=IDLE_TIMEOUT",flush=True)
            except Exception as exc:
                print(f"status=RECONNECT error={type(exc).__name__}:{exc}",flush=True)
                await asyncio.sleep(backoff)
                backoff = min(60,backoff*2)


async def main() -> None:
    collector = Collector()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT,signal.SIGTERM):
        loop.add_signal_handler(sig,collector.stop.set)
    try:
        await collector.run()
    finally:
        collector.close()


if __name__ == "__main__":
    asyncio.run(main())
