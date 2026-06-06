#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras


def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== NG SHORT BLOCK LIVE AUDIT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("RECENT_NG_SHORT_BLOCK_LOGIC_FROM_TRADES")
            cur.execute("""
                with ordered as (
                    select
                        id,
                        ts,
                        symbol,
                        upper(side) as side,
                        qty::numeric as qty,
                        price::numeric as price,
                        coalesce(nullif(strategy,''), payload->>'strategy', 'UNKNOWN') as strategy,
                        coalesce(origin, 'UNKNOWN') as origin,
                        coalesce(payload->>'reason', 'UNKNOWN') as reason
                    from trades
                    where symbol='NGN6@RTSX'
                      and coalesce(trade_source, '') = 'paper'
                      and coalesce(is_invalid, false) = false
                      and upper(side) in ('BUY','SELL')
                    order by ts, id
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
                            when side='SELL' and position_before = 0 then 'OPEN_SHORT'
                            when side='SELL' and position_before < 0 then 'ADD_SHORT'
                            when side='SELL' and position_before > 0 and position_before - qty = 0 then 'CLOSE_LONG'
                            when side='SELL' and position_before > 0 then 'REDUCE_LONG'
                            when side='BUY' and position_before < 0 and position_before + qty = 0 then 'CLOSE_SHORT'
                            when side='BUY' and position_before < 0 then 'REDUCE_SHORT'
                            when side='BUY' and position_before = 0 then 'OPEN_LONG'
                            when side='BUY' and position_before > 0 then 'ADD_LONG'
                            else 'UNKNOWN'
                        end as action
                    from pos
                )
                select
                    action,
                    count(*) as rows,
                    max(ts) as last_ts
                from actions
                where side='SELL'
                group by action
                order by action;
            """)
            for r in cur.fetchall():
                print(
                    f"ACTION_ROW action={r['action']} rows={r['rows']} "
                    f"last_ts={r['last_ts']}"
                )

            print()
            print("RECENT_BLOCK_CANDIDATES_AFTER_HOOK")
            cur.execute("""
                with ordered as (
                    select
                        id,
                        ts,
                        symbol,
                        upper(side) as side,
                        qty::numeric as qty,
                        price::numeric as price,
                        coalesce(nullif(strategy,''), payload->>'strategy', 'UNKNOWN') as strategy,
                        coalesce(origin, 'UNKNOWN') as origin,
                        coalesce(payload->>'reason', 'UNKNOWN') as reason
                    from trades
                    where symbol='NGN6@RTSX'
                      and coalesce(trade_source, '') = 'paper'
                      and coalesce(is_invalid, false) = false
                      and upper(side) in ('BUY','SELL')
                    order by ts, id
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
                )
                select
                    id, ts, symbol, side, qty, price, strategy, origin, reason,
                    position_before,
                    position_before - qty as position_after
                from pos
                where side='SELL'
                  and position_before <= 0
                order by ts desc, id desc
                limit 30;
            """)
            rows = cur.fetchall()
            print(f"RECENT_BLOCK_CANDIDATE_ROWS={len(rows)}")
            for r in rows:
                print(
                    f"BLOCK_CANDIDATE_ROW id={r['id']} ts={r['ts']} "
                    f"symbol={r['symbol']} side={r['side']} qty={r['qty']} "
                    f"price={r['price']} strategy={r['strategy']} origin={r['origin']} "
                    f"position_before={r['position_before']} position_after={r['position_after']} "
                    f"reason={r['reason']}"
                )

    print()
    print("VERDICT=CHECK_JOURNAL_FOR_PIPE_NG_SHORT_BLOCK_POLICY_V1")
    print("NG_SHORT_BLOCK_LIVE_AUDIT_V1_OK")


if __name__ == "__main__":
    main()
