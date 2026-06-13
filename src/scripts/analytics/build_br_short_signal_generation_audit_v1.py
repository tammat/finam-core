#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2


def table_exists(cur, table: str) -> bool:
    cur.execute("select to_regclass(%s) is not null;", (f"public.{table}",))
    return bool(cur.fetchone()[0])


def columns(cur, table: str) -> set[str]:
    cur.execute("""
        select column_name
        from information_schema.columns
        where table_schema='public'
          and table_name=%s
    """, (table,))
    return {r[0] for r in cur.fetchall()}


def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== BR SHORT SIGNAL GENERATION AUDIT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("goal=detect_whether_BR_SELL_is_short_entry_or_long_exit")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            print("TABLE_CHECK")
            for table in ("signals", "execution_intents", "trades", "fills"):
                print(f"TABLE_ROW table={table} exists={int(table_exists(cur, table))}")
            print()

            print("RAW_TRADES_SIDE_BALANCE")
            cur.execute("""
                select
                    symbol,
                    side,
                    count(*) as rows,
                    sum(qty) as qty_sum,
                    min(ts) as first_ts,
                    max(ts) as last_ts
                from trades
                where symbol in ('BRM6@RTSX','BRN6@RTSX')
                  and trade_source='paper'
                  and coalesce(is_invalid,false)=false
                group by symbol, side
                order by symbol, side;
            """)
            for symbol, side, rows, qty_sum, first_ts, last_ts in cur.fetchall():
                print(
                    f"TRADE_SIDE_ROW symbol={symbol} side={side} rows={rows} "
                    f"qty_sum={qty_sum} first_ts={first_ts} last_ts={last_ts}"
                )
            print()

            print("RUNNING_POSITION_AUDIT")
            cur.execute("""
                with x as (
                    select
                        symbol,
                        ts,
                        id,
                        side,
                        qty,
                        sum(case when side='BUY' then qty else -qty end)
                          over (
                              partition by symbol
                              order by ts, id
                              rows between unbounded preceding and current row
                          ) as running_qty
                    from trades
                    where symbol in ('BRM6@RTSX','BRN6@RTSX')
                      and trade_source='paper'
                      and coalesce(is_invalid,false)=false
                )
                select
                    symbol,
                    min(running_qty) as min_running_qty,
                    max(running_qty) as max_running_qty,
                    count(*) filter (where running_qty < 0) as short_state_rows,
                    count(*) filter (where running_qty = 0) as flat_state_rows,
                    count(*) filter (where running_qty > 0) as long_state_rows
                from x
                group by symbol
                order by symbol;
            """)
            total_short_state_rows = 0
            for symbol, min_qty, max_qty, short_rows, flat_rows, long_rows in cur.fetchall():
                total_short_state_rows += int(short_rows or 0)
                print(
                    f"POSITION_ROW symbol={symbol} min_running_qty={min_qty} "
                    f"max_running_qty={max_qty} short_state_rows={short_rows} "
                    f"flat_state_rows={flat_rows} long_state_rows={long_rows}"
                )
            print()

            print("SELL_CONTEXT_AUDIT")
            cur.execute("""
                with x as (
                    select
                        symbol,
                        ts,
                        id,
                        side,
                        qty,
                        price,
                        strategy,
                        timeframe,
                        origin,
                        sum(case when side='BUY' then qty else -qty end)
                          over (
                              partition by symbol
                              order by ts, id
                              rows between unbounded preceding and 1 preceding
                          ) as position_before,
                        sum(case when side='BUY' then qty else -qty end)
                          over (
                              partition by symbol
                              order by ts, id
                              rows between unbounded preceding and current row
                          ) as position_after
                    from trades
                    where symbol in ('BRM6@RTSX','BRN6@RTSX')
                      and trade_source='paper'
                      and coalesce(is_invalid,false)=false
                )
                select
                    symbol,
                    count(*) filter (where side='SELL') as sell_rows,
                    count(*) filter (
                        where side='SELL' and coalesce(position_before,0) <= 0
                    ) as sell_as_possible_short_entry,
                    count(*) filter (
                        where side='SELL' and coalesce(position_before,0) > 0
                    ) as sell_as_long_exit_or_reduce,
                    count(*) filter (
                        where side='SELL' and coalesce(position_after,0) < 0
                    ) as sell_resulted_short_position
                from x
                group by symbol
                order by symbol;
            """)
            possible_short_entry = 0
            resulted_short_position = 0
            for row in cur.fetchall():
                symbol, sell_rows, possible_entry, long_exit, resulted_short = row
                possible_short_entry += int(possible_entry or 0)
                resulted_short_position += int(resulted_short or 0)
                print(
                    f"SELL_CONTEXT_ROW symbol={symbol} sell_rows={sell_rows} "
                    f"sell_as_possible_short_entry={possible_entry} "
                    f"sell_as_long_exit_or_reduce={long_exit} "
                    f"sell_resulted_short_position={resulted_short}"
                )
            print()

            print("SELL_CONTEXT_SAMPLE")
            cur.execute("""
                with x as (
                    select
                        symbol,
                        ts,
                        id,
                        side,
                        qty,
                        price,
                        strategy,
                        timeframe,
                        origin,
                        trade_source,
                        sum(case when side='BUY' then qty else -qty end)
                          over (
                              partition by symbol
                              order by ts, id
                              rows between unbounded preceding and 1 preceding
                          ) as position_before,
                        sum(case when side='BUY' then qty else -qty end)
                          over (
                              partition by symbol
                              order by ts, id
                              rows between unbounded preceding and current row
                          ) as position_after
                    from trades
                    where symbol in ('BRM6@RTSX','BRN6@RTSX')
                      and trade_source='paper'
                      and coalesce(is_invalid,false)=false
                )
                select
                    id,
                    to_char(ts at time zone 'Europe/Moscow','YYYY-MM-DD HH24:MI:SS') as ts_msk,
                    symbol,
                    side,
                    qty,
                    price,
                    strategy,
                    timeframe,
                    origin,
                    coalesce(position_before,0) as position_before,
                    position_after
                from x
                where side='SELL'
                order by ts, id
                limit 40;
            """)
            for row in cur.fetchall():
                (
                    trade_id,
                    ts_msk,
                    symbol,
                    side,
                    qty,
                    price,
                    strategy,
                    timeframe,
                    origin,
                    position_before,
                    position_after,
                ) = row
                print(
                    f"SELL_SAMPLE_ROW id={trade_id} ts_msk={ts_msk} symbol={symbol} "
                    f"side={side} qty={qty} price={price} strategy={strategy} "
                    f"timeframe={timeframe} origin={origin} "
                    f"position_before={position_before} position_after={position_after}"
                )
            print()

            if table_exists(cur, "signals"):
                sig_cols = columns(cur, "signals")
                print("SIGNALS_AUDIT")
                print("SIGNALS_COLUMNS=" + ",".join(sorted(sig_cols)))

                if {"symbol", "side"}.issubset(sig_cols):
                    ts_col = "created_at" if "created_at" in sig_cols else ("ts" if "ts" in sig_cols else None)
                    strategy_col = "strategy" if "strategy" in sig_cols else "''"
                    timeframe_col = "timeframe" if "timeframe" in sig_cols else "''"

                    if ts_col:
                        cur.execute(f"""
                            select
                                symbol,
                                side,
                                count(*) as rows,
                                min({ts_col}) as first_ts,
                                max({ts_col}) as last_ts
                            from signals
                            where symbol in ('BRM6@RTSX','BRN6@RTSX')
                            group by symbol, side
                            order by symbol, side;
                        """)
                    else:
                        cur.execute("""
                            select
                                symbol,
                                side,
                                count(*) as rows,
                                null::timestamptz as first_ts,
                                null::timestamptz as last_ts
                            from signals
                            where symbol in ('BRM6@RTSX','BRN6@RTSX')
                            group by symbol, side
                            order by symbol, side;
                        """)
                    for symbol, side, rows, first_ts, last_ts in cur.fetchall():
                        print(
                            f"SIGNAL_SIDE_ROW symbol={symbol} side={side} "
                            f"rows={rows} first_ts={first_ts} last_ts={last_ts}"
                        )

                    if ts_col:
                        cur.execute(f"""
                            select
                                symbol,
                                side,
                                {strategy_col} as strategy,
                                {timeframe_col} as timeframe,
                                count(*) as rows
                            from signals
                            where symbol in ('BRM6@RTSX','BRN6@RTSX')
                            group by symbol, side, strategy, timeframe
                            order by symbol, side, strategy, timeframe;
                        """)
                        for symbol, side, strategy, timeframe, rows in cur.fetchall():
                            print(
                                f"SIGNAL_STRATEGY_ROW symbol={symbol} side={side} "
                                f"strategy={strategy} timeframe={timeframe} rows={rows}"
                            )
                else:
                    print("SIGNALS_SYMBOL_SIDE_COLUMNS_MISSING=1")
                print()

            if table_exists(cur, "execution_intents"):
                intent_cols = columns(cur, "execution_intents")
                print("EXECUTION_INTENTS_AUDIT")
                print("EXECUTION_INTENTS_COLUMNS=" + ",".join(sorted(intent_cols)))

                if {"symbol", "side"}.issubset(intent_cols):
                    ts_col = "created_at" if "created_at" in intent_cols else ("ts" if "ts" in intent_cols else None)
                    if ts_col:
                        cur.execute(f"""
                            select
                                symbol,
                                side,
                                count(*) as rows,
                                min({ts_col}) as first_ts,
                                max({ts_col}) as last_ts
                            from execution_intents
                            where symbol in ('BRM6@RTSX','BRN6@RTSX')
                            group by symbol, side
                            order by symbol, side;
                        """)
                    else:
                        cur.execute("""
                            select
                                symbol,
                                side,
                                count(*) as rows,
                                null::timestamptz as first_ts,
                                null::timestamptz as last_ts
                            from execution_intents
                            where symbol in ('BRM6@RTSX','BRN6@RTSX')
                            group by symbol, side
                            order by symbol, side;
                        """)
                    for symbol, side, rows, first_ts, last_ts in cur.fetchall():
                        print(
                            f"INTENT_SIDE_ROW symbol={symbol} side={side} "
                            f"rows={rows} first_ts={first_ts} last_ts={last_ts}"
                        )
                else:
                    print("EXECUTION_INTENTS_SYMBOL_SIDE_COLUMNS_MISSING=1")
                print()

    print("VERDICT")
    if total_short_state_rows > 0:
        print("VERDICT=BR_SHORT_POSITION_EXISTED")
    elif possible_short_entry > 0 and resulted_short_position == 0:
        print("VERDICT=BR_SELL_SIGNALS_EXIST_BUT_ONLY_REDUCE_LONG")
    else:
        print("VERDICT=BR_SHORT_SIGNAL_NOT_CONFIRMED")


if __name__ == "__main__":
    main()
