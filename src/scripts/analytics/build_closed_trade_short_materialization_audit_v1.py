#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2


def fetch_counts(cur, table: str, symbol_col: str = "symbol", side_col: str = "side"):
    cur.execute(f"""
        select
            coalesce({symbol_col}, 'NULL') as symbol,
            coalesce({side_col}, 'NULL') as side,
            count(*) as rows
        from {table}
        where coalesce({symbol_col}, '') like 'BR%'
        group by coalesce({symbol_col}, 'NULL'), coalesce({side_col}, 'NULL')
        order by symbol, side;
    """)
    return cur.fetchall()


def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== CLOSED TRADE SHORT MATERIALIZATION AUDIT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            print("RAW_TRADES_BR")
            raw_trades = fetch_counts(cur, "trades")
            for symbol, side, rows in raw_trades:
                print(f"RAW_TRADE_ROW symbol={symbol} side={side} rows={rows}")

            print()
            print("RAW_FILLS_BR")
            raw_fills = fetch_counts(cur, "fills")
            for symbol, side, rows in raw_fills:
                print(f"RAW_FILL_ROW symbol={symbol} side={side} rows={rows}")

            print()
            print("CLOSED_TRADES_BR")
            closed_trades = fetch_counts(cur, "closed_trades")
            for symbol, side, rows in closed_trades:
                print(f"CLOSED_TRADE_ROW symbol={symbol} side={side} rows={rows}")

            print()
            print("CLOSED_TRADES_ROOT_SYMBOL")
            cur.execute("""
                select
                    coalesce(root_symbol, 'NULL') as root_symbol,
                    coalesce(side, 'NULL') as side,
                    count(*) as rows
                from closed_trades
                group by coalesce(root_symbol, 'NULL'), coalesce(side, 'NULL')
                order by root_symbol, side;
            """)
            for root_symbol, side, rows in cur.fetchall():
                print(f"ROOT_ROW root_symbol={root_symbol} side={side} rows={rows}")

            print()
            print("SHORT_CLOSED_TRADES_SAMPLE")
            cur.execute("""
                select
                    id,
                    coalesce(symbol, 'NULL') as symbol,
                    coalesce(side, 'NULL') as side,
                    coalesce(root_symbol, 'NULL') as root_symbol,
                    coalesce(strategy, 'NULL') as strategy,
                    entry_ts,
                    exit_ts,
                    net_pnl
                from closed_trades
                where side = 'SHORT'
                order by coalesce(closed_at, exit_ts, created_at) desc
                limit 50;
            """)
            for row in cur.fetchall():
                trade_id, symbol, side, root_symbol, strategy, entry_ts, exit_ts, net_pnl = row
                print(
                    f"SHORT_SAMPLE_ROW id={trade_id} symbol={symbol} side={side} "
                    f"root_symbol={root_symbol} strategy={strategy} "
                    f"entry_ts={entry_ts} exit_ts={exit_ts} net_pnl={net_pnl}"
                )

            print()
            print("CHAIN_TABLE_CHECK")
            cur.execute("""
                select to_regclass('public.closed_trade_chains_v2') is not null;
            """)
            chain_exists = bool(cur.fetchone()[0])
            print(f"CHAIN_TABLE_EXISTS={int(chain_exists)}")

            chain_rows = []
            if chain_exists:
                cur.execute("""
                    select column_name
                    from information_schema.columns
                    where table_name='closed_trade_chains_v2'
                    order by ordinal_position;
                """)
                cols = [r[0] for r in cur.fetchall()]
                print("CHAIN_COLUMNS=" + ",".join(cols))

                if "symbol" in cols and "side" in cols:
                    cur.execute("""
                        select
                            coalesce(symbol, 'NULL') as symbol,
                            coalesce(side, 'NULL') as side,
                            count(*) as rows
                        from closed_trade_chains_v2
                        where coalesce(symbol, '') like 'BR%'
                        group by coalesce(symbol, 'NULL'), coalesce(side, 'NULL')
                        order by symbol, side;
                    """)
                    chain_rows = cur.fetchall()
                    for symbol, side, rows in chain_rows:
                        print(f"CHAIN_ROW symbol={symbol} side={side} rows={rows}")
                else:
                    print("CHAIN_SIDE_SYMBOL_COLUMNS_MISSING=1")

            print()
            print("CHAIN_TO_CLOSED_AUDIT")
            cur.execute("""
                with raw as (
                    select
                        symbol,
                        count(*) filter (where side='BUY') as raw_buy,
                        count(*) filter (where side='SELL') as raw_sell
                    from trades
                    where symbol like 'BR%'
                    group by symbol
                ),
                closed as (
                    select
                        symbol,
                        count(*) filter (where side='LONG') as closed_long,
                        count(*) filter (where side='SHORT') as closed_short
                    from closed_trades
                    where symbol like 'BR%'
                    group by symbol
                )
                select
                    coalesce(r.symbol, c.symbol) as symbol,
                    coalesce(r.raw_buy, 0) as raw_buy,
                    coalesce(r.raw_sell, 0) as raw_sell,
                    coalesce(c.closed_long, 0) as closed_long,
                    coalesce(c.closed_short, 0) as closed_short,
                    greatest(coalesce(r.raw_sell, 0) - coalesce(c.closed_short, 0), 0) as apparent_lost_short
                from raw r
                full join closed c on c.symbol = r.symbol
                order by symbol;
            """)
            lost_total = 0
            for symbol, raw_buy, raw_sell, closed_long, closed_short, lost_short in cur.fetchall():
                lost_total += int(lost_short or 0)
                print(
                    f"AUDIT_ROW symbol={symbol} raw_buy={raw_buy} raw_sell={raw_sell} "
                    f"closed_long={closed_long} closed_short={closed_short} "
                    f"apparent_lost_short={lost_short}"
                )

            print()
            print("NULL_ROOT_SHORT_AUDIT")
            cur.execute("""
                select
                    count(*) as null_root_short_rows
                from closed_trades
                where side='SHORT'
                  and root_symbol is null;
            """)
            null_root_short = int(cur.fetchone()[0] or 0)
            print(f"NULL_ROOT_SHORT_ROWS={null_root_short}")

    print()
    if lost_total > 0 and null_root_short > 0:
        print("VERDICT=SHORT_MATERIALIZATION_AND_ROOT_MAPPING_BROKEN")
    elif lost_total > 0:
        print("VERDICT=SHORT_LOST_IN_CLOSED_TRADES")
    elif null_root_short > 0:
        print("VERDICT=ROOT_SYMBOL_MAPPING_BROKEN")
    else:
        print("VERDICT=SHORT_MATERIALIZATION_OK")


if __name__ == "__main__":
    main()
