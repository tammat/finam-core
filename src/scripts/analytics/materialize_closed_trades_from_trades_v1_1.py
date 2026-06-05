#!/usr/bin/env python3
# Materialize closed_trades v1.1.
# Источник: public.trades.
# Исправляет:
# 1) entry_ts / exit_ts;
# 2) сторону сделки LONG/SHORT;
# 3) FIFO-паринг BUY/SELL;
# 4) replace-scope по symbol + source + trade_source.

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Any

import psycopg2
import psycopg2.extras


SOURCE = "closed_trade_engine_v1_1"


@dataclass
class Lot:
    symbol: str
    side: str          # LONG или SHORT
    qty: float
    price: float
    commission: float
    ts: Any
    strategy: str
    timeframe: str
    payload: dict


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--symbols", required=True)
    p.add_argument("--trade-source", default="paper")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--replace", action="store_true")
    return p.parse_args()


def get_conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(dsn)


def norm_strategy(row):
    return row["strategy"] or row["payload"].get("strategy") or row["payload"].get("replay_strategy") or ""


def norm_timeframe(row):
    return row["timeframe"] or row["payload"].get("replay_timeframe") or row["payload"].get("timeframe") or "unknown"


def gross_pnl(position_side, entry_price, exit_price, qty):
    if position_side == "LONG":
        return (exit_price - entry_price) * qty
    if position_side == "SHORT":
        return (entry_price - exit_price) * qty
    raise ValueError(f"unknown position side: {position_side}")


def build_closed_trades(rows):
    open_lots: dict[str, list[Lot]] = {}
    closed = []

    for r in rows:
        symbol = r["symbol"]
        side = r["side"].upper()
        qty_left = float(r["qty"])
        price = float(r["price"])
        commission = float(r["commission"] or 0)
        ts = r["ts"]
        payload = dict(r["payload"] or {})
        strategy = norm_strategy(r)
        timeframe = norm_timeframe(r)

        if side not in ("BUY", "SELL"):
            continue

        entry_side = "LONG" if side == "BUY" else "SHORT"
        opposite_side = "SHORT" if side == "BUY" else "LONG"

        lots = open_lots.setdefault(symbol, [])

        # Сначала закрываем противоположные открытые лоты.
        while qty_left > 0 and lots and lots[0].side == opposite_side:
            lot = lots[0]
            close_qty = min(qty_left, lot.qty)

            entry_commission_part = lot.commission * (close_qty / lot.qty) if lot.qty else 0
            exit_commission_part = commission * (close_qty / float(r["qty"])) if float(r["qty"]) else 0
            total_commission = entry_commission_part + exit_commission_part

            gpnl = gross_pnl(lot.side, lot.price, price, close_qty)
            npnl = gpnl - total_commission
            hold_seconds = int((ts - lot.ts).total_seconds()) if ts and lot.ts else 0

            closed.append({
                "symbol": symbol,
                "side": lot.side,
                "entry_price": lot.price,
                "exit_price": price,
                "qty": close_qty,
                "gross_pnl": gpnl,
                "net_pnl": npnl,
                "commission": total_commission,
                "strategy": lot.strategy or strategy,
                "timeframe": lot.timeframe or timeframe,
                "trade_source": r["trade_source"] or "paper",
                "entry_ts": lot.ts,
                "exit_ts": ts,
                "opened_at": lot.ts,
                "closed_at": ts,
                "holding_seconds": hold_seconds,
                "hold_seconds": float(hold_seconds),
                "root_symbol": payload.get("root_symbol"),
                "payload": {
                    "entry_payload": lot.payload,
                    "exit_payload": payload,
                    "entry_side": "BUY" if lot.side == "LONG" else "SELL",
                    "exit_side": side,
                    "materializer": SOURCE,
                },
            })

            lot.qty -= close_qty
            qty_left -= close_qty

            if lot.qty <= 1e-12:
                lots.pop(0)

        # Остаток открывает новый лот.
        if qty_left > 1e-12:
            lots.append(Lot(
                symbol=symbol,
                side=entry_side,
                qty=qty_left,
                price=price,
                commission=commission * (qty_left / float(r["qty"])) if float(r["qty"]) else 0,
                ts=ts,
                strategy=strategy,
                timeframe=timeframe,
                payload=payload,
            ))

    return closed


def main():
    args = parse_args()
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]

    print("=== MATERIALIZE CLOSED TRADES FROM TRADES V1.1 ===")
    print(f"mode={'APPLY' if args.apply else 'DRY_RUN'}")
    print(f"symbols={','.join(symbols)}")
    print(f"trade_source={args.trade_source}")
    print(f"source={SOURCE}")
    print()

    select_sql = """
        select
            id,
            symbol,
            side,
            qty,
            price,
            commission,
            fill_id,
            origin,
            payload,
            created_at,
            ts,
            trade_source,
            strategy,
            timeframe,
            continuous_symbol
        from trades
        where symbol = any(%s)
          and trade_source = %s
          and is_invalid = false
        order by symbol, ts, id
    """

    insert_sql = """
        insert into closed_trades (
            symbol, side, entry_price, exit_price, qty,
            gross_pnl, net_pnl, commission,
            strategy, timeframe, trade_source, source,
            entry_ts, exit_ts, opened_at, closed_at,
            holding_seconds, hold_seconds,
            root_symbol, payload
        )
        values (
            %(symbol)s, %(side)s, %(entry_price)s, %(exit_price)s, %(qty)s,
            %(gross_pnl)s, %(net_pnl)s, %(commission)s,
            %(strategy)s, %(timeframe)s, %(trade_source)s, %(source)s,
            %(entry_ts)s, %(exit_ts)s, %(opened_at)s, %(closed_at)s,
            %(holding_seconds)s, %(hold_seconds)s,
            %(root_symbol)s, %(payload)s
        )
    """

    delete_sql = """
        delete from closed_trades
        where symbol = any(%s)
          and trade_source = %s
          and source = %s
    """

    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(select_sql, (symbols, args.trade_source))
            rows = cur.fetchall()

            closed = build_closed_trades(rows)

            by_symbol = {}
            for t in closed:
                by_symbol[t["symbol"]] = by_symbol.get(t["symbol"], 0) + 1

            for symbol in symbols:
                fills = sum(1 for r in rows if r["symbol"] == symbol)
                trades = by_symbol.get(symbol, 0)
                print(f"SYMBOL_SUMMARY symbol={symbol} fills={fills} closed_trades={trades}")

            print(f"TOTAL_CLOSED_TRADES={len(closed)}")

            if not args.apply:
                print("VERDICT=DRY_RUN")
                return

            if args.replace:
                cur.execute(delete_sql, (symbols, args.trade_source, SOURCE))
                print(f"REPLACED_ROWS={cur.rowcount}")

            for t in closed:
                t["source"] = SOURCE
                t["payload"] = psycopg2.extras.Json(t["payload"])
                cur.execute(insert_sql, t)

            conn.commit()

    print("VERDICT=APPLIED")


if __name__ == "__main__":
    main()
