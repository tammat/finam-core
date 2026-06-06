#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2


def exists(cur, table: str) -> bool:
    cur.execute("select to_regclass(%s) is not null;", (f"public.{table}",))
    return bool(cur.fetchone()[0])


def cols(cur, table: str) -> set[str]:
    cur.execute("""
        select column_name
        from information_schema.columns
        where table_schema='public'
          and table_name=%s
    """, (table,))
    return {r[0] for r in cur.fetchall()}


def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== BR SHORT ENTRY ENABLEMENT RESEARCH V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("goal=find_layer_preventing_BR_open_short")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            print("SIGNAL_LAYER")
            if exists(cur, "signals"):
                cur.execute("""
                    select
                        symbol,
                        side,
                        status,
                        strategy,
                        count(*) as rows
                    from signals
                    where symbol in ('BRM6@RTSX','BRN6@RTSX')
                    group by symbol, side, status, strategy
                    order by symbol, side, status, strategy;
                """)
                for symbol, side, status, strategy, rows in cur.fetchall():
                    print(
                        f"SIGNAL_ROW symbol={symbol} side={side} status={status} "
                        f"strategy={strategy} rows={rows}"
                    )
            else:
                print("SIGNALS_TABLE_MISSING=1")

            print()
            print("EXECUTION_INTENT_LAYER")
            if exists(cur, "execution_intents"):
                c = cols(cur, "execution_intents")
                print("EXECUTION_INTENTS_COLUMNS=" + ",".join(sorted(c)))

                if {"symbol", "side"}.issubset(c):
                    cur.execute("""
                        select
                            symbol,
                            side,
                            intent_state,
                            reason,
                            count(*) as rows
                        from execution_intents
                        where symbol in ('BRM6@RTSX','BRN6@RTSX')
                        group by symbol, side, intent_state, reason
                        order by symbol, side, intent_state, reason;
                    """)
                    for symbol, side, state, reason, rows in cur.fetchall():
                        print(
                            f"INTENT_ROW symbol={symbol} side={side} "
                            f"state={state} reason={reason} rows={rows}"
                        )
                else:
                    print("EXECUTION_INTENTS_SYMBOL_SIDE_MISSING=1")
            else:
                print("EXECUTION_INTENTS_TABLE_MISSING=1")

            print()
            print("ORDER_LAYER")
            if exists(cur, "orders"):
                c = cols(cur, "orders")
                print("ORDERS_COLUMNS=" + ",".join(sorted(c)))

                if {"symbol", "side"}.issubset(c):
                    state_expr = "status" if "status" in c else ("state" if "state" in c else "''")
                    cur.execute(f"""
                        select
                            symbol,
                            side,
                            {state_expr} as state,
                            count(*) as rows
                        from orders
                        where symbol in ('BRM6@RTSX','BRN6@RTSX')
                        group by symbol, side, state
                        order by symbol, side, state;
                    """)
                    for symbol, side, state, rows in cur.fetchall():
                        print(
                            f"ORDER_ROW symbol={symbol} side={side} state={state} rows={rows}"
                        )
                else:
                    print("ORDERS_SYMBOL_SIDE_MISSING=1")
            else:
                print("ORDERS_TABLE_MISSING=1")

            print()
            print("TRADE_POSITION_LAYER")
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
                    count(*) filter (where side='SELL' and coalesce(position_before,0) <= 0) as sell_when_flat_or_short,
                    count(*) filter (where side='SELL' and coalesce(position_before,0) > 0) as sell_when_long,
                    count(*) filter (where side='SELL' and coalesce(position_after,0) < 0) as sell_opened_short,
                    min(position_after) as min_position_after,
                    max(position_after) as max_position_after
                from x
                group by symbol
                order by symbol;
            """)
            total_sell_opened_short = 0
            for row in cur.fetchall():
                (
                    symbol,
                    sell_rows,
                    sell_flat,
                    sell_long,
                    sell_opened_short,
                    min_after,
                    max_after,
                ) = row
                total_sell_opened_short += int(sell_opened_short or 0)
                print(
                    f"POSITION_ENABLEMENT_ROW symbol={symbol} sell_rows={sell_rows} "
                    f"sell_when_flat_or_short={sell_flat} sell_when_long={sell_long} "
                    f"sell_opened_short={sell_opened_short} "
                    f"min_position_after={min_after} max_position_after={max_after}"
                )

            print()
            print("CODE_SEARCH_HINTS")
            print("SEARCH_HINT grep='BR_SHORT_ONLY_ENABLED'")
            print("SEARCH_HINT grep='allow_short|short_only|SELL|OPEN_SHORT|reduce_only|position_before'")
            print("SEARCH_HINT probable_layer='signal_semantics_or_execution_position_policy'")

    print()
    if total_sell_opened_short > 0:
        print("VERDICT=BR_OPEN_SHORT_ALREADY_ENABLED")
    else:
        print("VERDICT=BR_OPEN_SHORT_NOT_ENABLED")


if __name__ == "__main__":
    main()
