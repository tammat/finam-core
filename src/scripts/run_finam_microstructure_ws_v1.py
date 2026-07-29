from __future__ import annotations

import asyncio
import json
import os
import re
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
        "SBER@MISX,LKOH@MISX,GAZP@MISX,PLZL@MISX,USDRUBF@RTSX,BRQ6@RTSX,NGQ6@RTSX,MXU6@RTSX",
    ).split(",") if item.strip()
)
SOURCE = "FINAM_MICROSTRUCTURE_WS_V1"
DATA_STALE_AFTER_SEC = float(os.getenv("MARKETCORE_MICROSTRUCTURE_DATA_STALE_AFTER_SEC", "90"))
MAX_SYMBOLS = int(os.getenv("MARKETCORE_MICROSTRUCTURE_MAX_SYMBOLS", "10"))
MAX_DETAIL_SYMBOLS = int(os.getenv("MARKETCORE_MICROSTRUCTURE_MAX_DETAIL_SYMBOLS", "8"))
PRIORITY_REFRESH_SECONDS = int(os.getenv("MARKETCORE_MICROSTRUCTURE_PRIORITY_REFRESH_SECONDS", "300"))
FUTURES_MONTH = {code: month for month, code in enumerate("FGHJKMNQUVXZ", start=1)}
FUTURES_RE = re.compile(r"^[A-Z]+([FGHJKMNQUVXZ])(\d)@RTSX$")


class StaleDataError(RuntimeError):
    pass


def data_is_stale(last_persisted_at: float, now: float, threshold_seconds: float) -> bool:
    return now-last_persisted_at >= threshold_seconds


def finam_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper()
    if symbol in {"IMOEX", "IMOEX2", "RTSI"}:
        return f"{symbol}@MISX"
    return symbol


def contract_is_current(symbol: str, now: datetime | None = None) -> bool:
    """Reject expired RTS futures before asking Finam for a subscription."""
    match = FUTURES_RE.fullmatch(symbol.strip().upper())
    if not match:
        return True
    current = now or datetime.now(timezone.utc)
    year_digit = int(match.group(2))
    decade = current.year-current.year % 10
    contract_year = decade+year_digit
    if contract_year < current.year-5:
        contract_year += 10
    contract_month = FUTURES_MONTH[match.group(1)]
    return (contract_year, contract_month) >= (current.year, current.month)


def merge_symbols(*groups: list[str] | tuple[str, ...], limit: int = MAX_SYMBOLS) -> tuple[str, ...]:
    symbols: list[str] = []
    for group in groups:
        for raw_symbol in group:
            symbol = finam_symbol(raw_symbol)
            if symbol and contract_is_current(symbol) and symbol not in symbols:
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


def first_number(payload: dict[str, Any], *names: str) -> Decimal | None:
    """Accept Finam camelCase and legacy snake_case payloads."""
    for name in names:
        if name in payload:
            parsed = number(payload.get(name))
            if parsed is not None:
                return parsed
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
        def query(source: str, sql: str) -> list[str]:
            try:
                with self.conn.cursor() as cur:
                    cur.execute(sql)
                    return [str(row[0]) for row in cur.fetchall()]
            except psycopg2.Error as exc:
                print(
                    f"universe_source={source} status=SKIPPED db_error={exc.pgcode or type(exc).__name__}",
                    flush=True,
                )
                return []

        watched = query("MARKET_DATA_WATCH", """
            SELECT symbol FROM public.market_data_watch_universe
            WHERE is_enabled ORDER BY symbol
        """)
        shadow = query("SHADOW", """
            SELECT DISTINCT symbol
            FROM analytics.forward_edge_shadow_trade_v1
            WHERE cohort_id=(
                SELECT cohort_id FROM analytics.forward_edge_shadow_trade_v1
                ORDER BY created_at DESC LIMIT 1
            )
        """)
        recent_fills = query("PAPER_FILLS", """
            SELECT DISTINCT symbol FROM public.signal_fills
            WHERE created_at >= current_date-1
        """)
        dynamic_priority = query("DYNAMIC_PRIORITY", """
            SELECT symbol
            FROM analytics.microstructure_research_priority_v1
            WHERE selected_for_detail
            ORDER BY priority_rank
        """)
        asset_branches = query("V5_ASSET_BRANCHES", """
            SELECT symbol
            FROM analytics.v5_asset_branch_policy_v1
            WHERE enabled AND asset_code IN ('USD', 'GOLD', 'CNY')
            ORDER BY array_position(ARRAY['USD','GOLD','CNY']::text[], asset_code),
                     timeframe_code, side_code
        """)
        # The first symbols receive ORDER_BOOK and trade-tape subscriptions.
        # Keep active OOS instruments ahead of opportunistic Paper traffic so a
        # busy signal stream cannot evict the cohort that must be validated.
        # USD/GOLD/CNY are explicitly shown as accumulation branches in the UI.
        # Keep them in the bounded subscription set so they cannot be evicted by
        # opportunistic recent fills from unrelated symbols.
        return merge_symbols(asset_branches, dynamic_priority, recent_fills, shadow, SYMBOLS, watched)

    def close(self) -> None:
        self.token_manager.close()
        self.conn.close()

    async def subscribe(self, ws: Any, token: str, symbols: tuple[str, ...]) -> None:
        await ws.send(json.dumps({
            "action": "SUBSCRIBE", "type": "QUOTES",
            "data": {"symbols": list(symbols)}, "token": token,
        }))
        detail_symbols = symbols[:MAX_DETAIL_SYMBOLS]
        for symbol in detail_symbols:
            for subscription_type in ("ORDER_BOOK", "INSTRUMENT_TRADES"):
                await ws.send(json.dumps({
                    "action": "SUBSCRIBE", "type": subscription_type,
                    "data": {"symbol": symbol}, "token": token,
                }))
                await asyncio.sleep(0.05)
        print(
            f"subscriptions=QUOTES:{len(symbols)},DETAIL:{len(detail_symbols)} "
            f"requests={1+2*len(detail_symbols)}",
            flush=True,
        )

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
        bid_size = first_number(quote, "bidSize", "bid_size")
        ask_size = first_number(quote, "askSize", "ask_size")
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
                    while not self.stop.is_set() and time.monotonic()-connected_at < PRIORITY_REFRESH_SECONDS:
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
