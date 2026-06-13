#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras


SYMBOLS = ("NGN6@RTSX",)


def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== NG SHORT SIGNAL SEMANTICS AUDIT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("goal=detect_NG_SELL_semantics_open_short_or_close_long")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("TRADE_ACTION_SUMMARY")
            cur.execute(
                """
                with ordered as (
                    select
                        id,
                        ts,
                        symbol,
                        upper(side) as side,
                        qty::numeric as qty,
                        price,
                        coalesce(strategy, payload->>'strategy', 'UNKNOWN') as strategy,
                        coalesce(origin, 'UNKNOWN') as origin
                    from trades
                    where symbol = any(%s)
                      and coalesce(trade_source, '') = 'paper'
                      and coalesce(is_invalid, false) = false
                      and upper(side) in ('BUY','SELL')
                    order by symbol, ts, id
                ),
                pos as (
                    select
                        *,
                        coalesce(
                            sum(case when side='BUY' then qty else -qty end)
                            over (
                                partition by symbol
                                order by ts, id
                                rows between unbounded preceding and 1 preceding
                            ),
                            0
                        ) as position_before
                    from ordered
                ),
                actions as (
                    select
                        *,
                        position_before + case when side='BUY' then qty else -qty end as position_after,
                        case
                            when side='BUY' and position_before >= 0 then
                                case when position_before = 0 then 'OPEN_LONG' else 'ADD_LONG' end
                            when side='SELL' and position_before > 0 then
                                case when position_before - qty = 0 then 'CLOSE_LONG' else 'REDUCE_LONG' end
                            when side='SELL' and position_before <= 0 then
                                case when position_before = 0 then 'OPEN_SHORT' else 'ADD_SHORT' end
                            when side='BUY' and position_before < 0 then
                                case when position_before + qty = 0 then 'CLOSE_SHORT' else 'REDUCE_SHORT' end
                            else 'UNKNOWN'
                        end as action
                    from pos
                )
                select symbol, side, action, count(*) as rows
                from actions
                group by symbol, side, action
                order by symbol, side, action;
                """,
                (list(SYMBOLS),),
            )
            for r in cur.fetchall():
                print(
                    f"TRADE_ACTION_ROW symbol={r['symbol']} side={r['side']} "
                    f"action={r['action']} rows={r['rows']}"
                )
            print()

            print("NG_SELL_TRADE_SEMANTICS")
            cur.execute(
                """
                with ordered as (
                    select
                        id,
                        ts,
                        symbol,
                        upper(side) as side,
                        qty::numeric as qty
                    from trades
                    where symbol = any(%s)
                      and coalesce(trade_source, '') = 'paper'
                      and coalesce(is_invalid, false) = false
                      and upper(side) in ('BUY','SELL')
                    order by symbol, ts, id
                ),
                pos as (
                    select
                        *,
                        coalesce(
                            sum(case when side='BUY' then qty else -qty end)
                            over (
                                partition by symbol
                                order by ts, id
                                rows between unbounded preceding and 1 preceding
                            ),
                            0
                        ) as position_before
                    from ordered
                ),
                actions as (
                    select
                        *,
                        position_before + case when side='BUY' then qty else -qty end as position_after,
                        case
                            when side='SELL' and position_before <= 0 then
                                case when position_before = 0 then 'OPEN_SHORT' else 'ADD_SHORT' end
                            when side='SELL' and position_before > 0 then
                                case when position_before - qty = 0 then 'CLOSE_LONG' else 'REDUCE_LONG' end
                            else 'OTHER'
                        end as action
                    from pos
                )
                select
                    count(*) filter (where side='SELL') as sell_rows,
                    count(*) filter (where side='SELL' and action='OPEN_SHORT') as sell_open_short,
                    count(*) filter (where side='SELL' and action='ADD_SHORT') as sell_add_short,
                    count(*) filter (where side='SELL' and action='REDUCE_LONG') as sell_reduce_long,
                    count(*) filter (where side='SELL' and action='CLOSE_LONG') as sell_close_long
                from actions;
                """,
                (list(SYMBOLS),),
            )
            r = cur.fetchone()
            sell_rows = int(r["sell_rows"] or 0)
            sell_open_short = int(r["sell_open_short"] or 0)
            sell_add_short = int(r["sell_add_short"] or 0)
            sell_reduce_long = int(r["sell_reduce_long"] or 0)
            sell_close_long = int(r["sell_close_long"] or 0)

            print(f"SELL_ROWS={sell_rows}")
            print(f"SELL_OPEN_SHORT={sell_open_short}")
            print(f"SELL_ADD_SHORT={sell_add_short}")
            print(f"SELL_REDUCE_LONG={sell_reduce_long}")
            print(f"SELL_CLOSE_LONG={sell_close_long}")
            print()

            print("SIGNAL_LAYER_SUMMARY")
            cur.execute(
                """
                select
                    symbol,
                    coalesce(strategy, payload->>'strategy', 'UNKNOWN') as strategy,
                    upper(side) as side,
                    coalesce(status, 'UNKNOWN') as status,
                    count(*) as rows
                from signals
                where symbol = any(%s)
                group by
                    symbol,
                    coalesce(strategy, payload->>'strategy', 'UNKNOWN'),
                    upper(side),
                    coalesce(status, 'UNKNOWN')
                order by symbol, strategy, side, status;
                """,
                (list(SYMBOLS),),
            )
            for r in cur.fetchall():
                print(
                    f"SIGNAL_ROW symbol={r['symbol']} strategy={r['strategy']} "
                    f"side={r['side']} status={r['status']} rows={r['rows']}"
                )
            print()

            print("SELL_SIGNAL_REASONS")
            cur.execute(
                """
                select
                    coalesce(payload->>'reason', rejection_reason, 'UNKNOWN') as reason,
                    count(*) as rows
                from signals
                where symbol = any(%s)
                  and upper(side) = 'SELL'
                group by coalesce(payload->>'reason', rejection_reason, 'UNKNOWN')
                order by rows desc, reason
                limit 30;
                """,
                (list(SYMBOLS),),
            )
            for r in cur.fetchall():
                print(f"SELL_SIGNAL_REASON_ROW reason={r['reason']} rows={r['rows']}")
            print()

            print("SELL_TRADE_SAMPLE")
            cur.execute(
                """
                with ordered as (
                    select
                        id,
                        ts,
                        symbol,
                        upper(side) as side,
                        qty::numeric as qty,
                        price,
                        coalesce(strategy, payload->>'strategy', 'UNKNOWN') as strategy,
                        coalesce(origin, 'UNKNOWN') as origin,
                        coalesce(payload->>'reason', 'UNKNOWN') as reason
                    from trades
                    where symbol = any(%s)
                      and coalesce(trade_source, '') = 'paper'
                      and coalesce(is_invalid, false) = false
                      and upper(side) in ('BUY','SELL')
                    order by symbol, ts, id
                ),
                pos as (
                    select
                        *,
                        coalesce(
                            sum(case when side='BUY' then qty else -qty end)
                            over (
                                partition by symbol
                                order by ts, id
                                rows between unbounded preceding and 1 preceding
                            ),
                            0
                        ) as position_before
                    from ordered
                ),
                actions as (
                    select
                        *,
                        position_before + case when side='BUY' then qty else -qty end as position_after,
                        case
                            when side='SELL' and position_before <= 0 then
                                case when position_before = 0 then 'OPEN_SHORT' else 'ADD_SHORT' end
                            when side='SELL' and position_before > 0 then
                                case when position_before - qty = 0 then 'CLOSE_LONG' else 'REDUCE_LONG' end
                            else 'OTHER'
                        end as action
                    from pos
                )
                select *
                from actions
                where side='SELL'
                order by ts desc, id desc
                limit 80;
                """,
                (list(SYMBOLS),),
            )
            for r in cur.fetchall():
                print(
                    f"SELL_TRADE_ROW id={r['id']} ts={r['ts']} symbol={r['symbol']} "
                    f"side={r['side']} qty={r['qty']} price={r['price']} "
                    f"strategy={r['strategy']} origin={r['origin']} "
                    f"position_before={r['position_before']} action={r['action']} "
                    f"position_after={r['position_after']} reason={r['reason']}"
                )
            print()

            print("FINAL_POSITIONS")
            cur.execute(
                """
                select
                    symbol,
                    sum(case when upper(side)='BUY' then qty::numeric else -qty::numeric end) as final_position
                from trades
                where symbol = any(%s)
                  and coalesce(trade_source, '') = 'paper'
                  and coalesce(is_invalid, false) = false
                  and upper(side) in ('BUY','SELL')
                group by symbol
                order by symbol;
                """,
                (list(SYMBOLS),),
            )
            for r in cur.fetchall():
                print(f"FINAL_POSITION_ROW symbol={r['symbol']} final_position={r['final_position']}")
            print()

    if sell_rows == 0:
        verdict = "NG_SELL_SIGNALS_ABSENT"
    elif sell_open_short + sell_add_short > 0:
        verdict = "NG_SHORT_SEMANTICS_PRESENT"
    elif sell_reduce_long + sell_close_long == sell_rows:
        verdict = "NG_SELL_ONLY_REDUCE_OR_CLOSE_LONG"
    else:
        verdict = "NG_MIXED_SELL_SEMANTICS"

    print(f"VERDICT={verdict}")
    print("NG_SHORT_SIGNAL_SEMANTICS_AUDIT_V1_OK")


if __name__ == "__main__":
    main()
