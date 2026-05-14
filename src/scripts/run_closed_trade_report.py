# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import psycopg2
from collections import defaultdict

from finam_core.analytics.closed_trade_repository import ClosedTradeRepository
from finam_core.analytics.closed_trade_engine import (
    ClosedTradeEngine,
    TradeFill,
    summarize_closed_trades,
)


def load_fills(conn) -> list[TradeFill]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                t.id,
                t.ts,
                t.symbol,
                t.side,
                t.qty,
                t.price,
                t.commission,
                t.fill_id,
                coalesce(t.payload, '{}'::jsonb) ||
                jsonb_strip_nulls(
                    jsonb_build_object(
                        'signal_id', s.signal_id,
                        'strategy', s.strategy,
                        'horizon', s.horizon,
                        'regime', s.regime,
                        'timeframe', s.timeframe
                    )
                ) as payload
            FROM trades t
            LEFT JOIN signal_fills sf
                ON sf.fill_id = t.fill_id
            LEFT JOIN signals s
                ON s.signal_id = sf.signal_id
            WHERE (
                    t.origin = 'paper'
                    OR t.trade_source = 'paper'
                    OR t.payload::text ILIKE '%paper%'
                  )
              AND COALESCE(t.origin, '') != 'backfill_from_fills'
            ORDER BY t.symbol, t.ts, t.id
            """
        )

        rows = cur.fetchall()

    return [
        TradeFill(
            id=int(r[0]),
            ts=str(r[1]),
            symbol=str(r[2]),
            side=str(r[3]),
            qty=float(r[4]),
            price=float(r[5]),
            commission=float(r[6] or 0.0),
            fill_id=r[7],
            payload=r[8] if isinstance(r[8], dict) else {},
        )
        for r in rows
    ]


def print_summary(title: str, summary: dict) -> None:
    print("")
    print(title)
    print("-" * len(title))
    print(f"trades        : {summary['trades']}")
    print(f"wins          : {summary['wins']}")
    print(f"losses        : {summary['losses']}")
    print(f"winrate       : {summary['winrate']:.2f}%")
    print(f"gross_pnl     : {summary['gross_pnl']:.2f}")
    print(f"net_pnl       : {summary['net_pnl']:.2f}")
    print(f"profit_factor : {summary['profit_factor']:.2f}")
    print(f"expectancy    : {summary['expectancy']:.2f}")


def main() -> None:
    conn = psycopg2.connect(
        dbname=os.getenv("PGDATABASE", "finam_core"),
        user=os.getenv("PGUSER") or None,
        host=os.getenv("PGHOST") or None,
        port=os.getenv("PGPORT") or None,
        password=os.getenv("PGPASSWORD") or None,
    )

    fills = load_fills(conn)

    engine = ClosedTradeEngine()
    closed = engine.build_closed_trades(fills)

    repo = ClosedTradeRepository(conn)
    saved = repo.save_closed_trades(closed, trade_source="paper")

    summary = summarize_closed_trades(closed)
    print(f"CLOSED_TRADES_SAVED saved={saved} total={len(closed)}", flush=True)
    print_summary("CLOSED TRADE SUMMARY", summary)

    by_symbol = defaultdict(list)
    for trade in closed:
        by_symbol[trade.symbol].append(trade)

    for symbol, trades in sorted(by_symbol.items()):
        print_summary(f"SYMBOL {symbol}", summarize_closed_trades(trades))

    by_source_symbol = defaultdict(list)
    for trade in closed:
        payload = trade.payload or {}
        entry_payload = payload.get("entry_payload") or {}
        source = entry_payload.get("origin") or entry_payload.get("trade_source") or entry_payload.get("execution_type") or "unknown"
        by_source_symbol[(source, trade.symbol)].append(trade)

    for (source, symbol), trades in sorted(by_source_symbol.items()):
        print_summary(f"SOURCE {source} SYMBOL {symbol}", summarize_closed_trades(trades))

    print("")
    print("LAST CLOSED TRADES")
    print("------------------")

    for trade in closed[-20:]:
        print(
            f"{trade.symbol} {trade.side} qty={trade.qty} "
            f"entry={trade.entry_price:.4f} exit={trade.exit_price:.4f} "
            f"net_pnl={trade.net_pnl:.2f} "
            f"entry_ts={trade.entry_ts} exit_ts={trade.exit_ts}"
        )


if __name__ == "__main__":
    main()
