#!/usr/bin/env python3
# Аудит расхождений closed_trades после materialize.
# Проверяет распределение по source/trade_source/strategy/timeframe/side
# и показывает строки, которые попадают в отчёт, но могли не входить в replace-scope.

from __future__ import annotations

import argparse
import os
import psycopg2


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--symbols", required=True)
    return p.parse_args()


def conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(dsn)


def main():
    args = parse_args()
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]

    print("=== CLOSED TRADES RECONCILIATION AUDIT V1 ===")
    print(f"symbols={','.join(symbols)}")
    print()

    sql_scope = """
        select
          symbol,
          source,
          trade_source,
          strategy,
          timeframe,
          side,
          count(*) as trades,
          min(created_at) as first_created,
          max(created_at) as last_created,
          min(entry_ts) as first_entry_ts,
          max(exit_ts) as last_exit_ts,
          sum(net_pnl) as net_pnl
        from closed_trades
        where symbol = any(%s)
        group by symbol, source, trade_source, strategy, timeframe, side
        order by symbol, source, trade_source, strategy, timeframe, side;
    """

    sql_recent = """
        select
          id,
          symbol,
          side,
          strategy,
          timeframe,
          source,
          trade_source,
          entry_ts,
          exit_ts,
          entry_price,
          exit_price,
          qty,
          gross_pnl,
          commission,
          net_pnl,
          holding_seconds
        from closed_trades
        where symbol = any(%s)
        order by symbol, exit_ts nulls last, id
        limit 80;
    """

    sql_duplicates = """
        select
          symbol,
          strategy,
          timeframe,
          side,
          entry_ts,
          exit_ts,
          entry_price,
          exit_price,
          qty,
          count(*) as duplicates,
          sum(net_pnl) as net_pnl
        from closed_trades
        where symbol = any(%s)
        group by symbol, strategy, timeframe, side, entry_ts, exit_ts, entry_price, exit_price, qty
        having count(*) > 1
        order by duplicates desc, symbol, exit_ts;
    """

    with conn() as c:
        with c.cursor() as cur:
            print("SCOPE_BREAKDOWN")
            cur.execute(sql_scope, (symbols,))
            for r in cur.fetchall():
                print("SCOPE_ROW " + " ".join(f"{k}={v}" for k, v in zip(
                    [
                        "symbol", "source", "trade_source", "strategy", "timeframe",
                        "side", "trades", "first_created", "last_created",
                        "first_entry_ts", "last_exit_ts", "net_pnl"
                    ],
                    r
                )))
            print()

            print("DUPLICATES")
            cur.execute(sql_duplicates, (symbols,))
            dup_rows = cur.fetchall()
            if not dup_rows:
                print("DUPLICATES_NONE")
            else:
                for r in dup_rows:
                    print("DUPLICATE_ROW " + " ".join(f"{k}={v}" for k, v in zip(
                        [
                            "symbol", "strategy", "timeframe", "side", "entry_ts",
                            "exit_ts", "entry_price", "exit_price", "qty",
                            "duplicates", "net_pnl"
                        ],
                        r
                    )))
            print()

            print("ROWS")
            cur.execute(sql_recent, (symbols,))
            for r in cur.fetchall():
                print("TRADE_ROW " + " ".join(f"{k}={v}" for k, v in zip(
                    [
                        "id", "symbol", "side", "strategy", "timeframe", "source",
                        "trade_source", "entry_ts", "exit_ts", "entry_price",
                        "exit_price", "qty", "gross_pnl", "commission",
                        "net_pnl", "holding_seconds"
                    ],
                    r
                )))

    print()
    print("VERDICT=OK")


if __name__ == "__main__":
    main()
