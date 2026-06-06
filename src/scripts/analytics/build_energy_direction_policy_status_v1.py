#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras


def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== ENERGY DIRECTION POLICY STATUS V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("scope=BR_NG_DIRECTION_POLICY")
    print()

    rows = [
        {
            "root": "BR",
            "long_policy": "SHADOW_OR_BLOCKED_AFTER_NEGATIVE_LONG_STAT",
            "short_policy": "SHADOW_ENABLED_FOR_CANONICAL_BR_CONSERVATIVE_BREAKOUT",
            "live_enforcement": "BR_SHORT_SHADOW_HOOK_INSTALLED; BR_PAPER_SHORT_ENABLEMENT_INSTALLED",
            "status": "BR_SHORT_RESEARCH_POSITIVE_BUT_LIVE_ROWS_PENDING",
            "checkpoint": "checkpoint_br_short_paper_enablement_v1",
        },
        {
            "root": "NG",
            "long_policy": "ALLOWED",
            "short_policy": "BLOCKED_AFTER_NEGATIVE_SHORT_EDGE",
            "live_enforcement": "NG_SHORT_BLOCK_POLICY_AND_PIPELINE_HOOK_INSTALLED",
            "status": "NG_SHORT_BLOCKED; LONG_AND_LONG_EXIT_ALLOWED",
            "checkpoint": "checkpoint_ng_short_block_live_audit_v1",
        },
    ]

    print("POLICY_STATUS")
    for r in rows:
        print(
            f"POLICY_ROW root={r['root']} "
            f"long_policy={r['long_policy']} "
            f"short_policy={r['short_policy']} "
            f"live_enforcement={r['live_enforcement']} "
            f"status={r['status']} "
            f"checkpoint={r['checkpoint']}"
        )
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            print("RECENT_TRADES_BY_ROOT_SIDE")
            cur.execute("""
                select
                    case
                        when symbol like 'BR%' then 'BR'
                        when symbol like 'NG%' then 'NG'
                        else 'OTHER'
                    end as root,
                    symbol,
                    upper(side) as side,
                    count(*) as rows,
                    max(ts) as last_ts
                from trades
                where symbol like any(array['BR%','NG%'])
                  and coalesce(trade_source, '') = 'paper'
                  and coalesce(is_invalid, false) = false
                group by root, symbol, upper(side)
                order by root, symbol, side;
            """)
            for r in cur.fetchall():
                print(
                    f"TRADE_ROW root={r['root']} symbol={r['symbol']} "
                    f"side={r['side']} rows={r['rows']} last_ts={r['last_ts']}"
                )
            print()

            print("NG_SHORT_BLOCK_STATUS")
            cur.execute("""
                with ordered as (
                    select
                        id, ts, symbol, upper(side) as side,
                        qty::numeric as qty,
                        price::numeric as price
                    from trades
                    where symbol like 'NG%'
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
                        case
                            when side='SELL' and position_before = 0 then 'OPEN_SHORT'
                            when side='SELL' and position_before < 0 then 'ADD_SHORT'
                            when side='SELL' and position_before > 0 and position_before - qty = 0 then 'CLOSE_LONG'
                            when side='SELL' and position_before > 0 then 'REDUCE_LONG'
                            else 'OTHER'
                        end as action
                    from pos
                    where side='SELL'
                )
                select action, count(*) as rows, max(ts) as last_ts
                from actions
                group by action
                order by action;
            """)
            for r in cur.fetchall():
                print(
                    f"NG_ACTION_ROW action={r['action']} rows={r['rows']} last_ts={r['last_ts']}"
                )
            print()

            print("BR_SHORT_SHADOW_STATUS")
            cur.execute("""
                select to_regclass('public.br_short_shadow_events_v1') is not null as exists;
            """)
            exists = bool(cur.fetchone()["exists"])
            print(f"BR_SHORT_SHADOW_TABLE_EXISTS={int(exists)}")

            if exists:
                cur.execute("""
                    select
                        count(*) as rows,
                        count(*) filter (where side='SELL') as sell_rows,
                        max(created_at) as last_created_at
                    from br_short_shadow_events_v1;
                """)
                r = cur.fetchone()
                print(
                    f"BR_SHORT_SHADOW_ROW rows={r['rows']} "
                    f"sell_rows={r['sell_rows']} last_created_at={r['last_created_at']}"
                )

    print()
    print("DECISION_SUMMARY")
    print("BR_LONG=SHADOW_OR_BLOCKED")
    print("BR_SHORT=SHADOW/PAPER_ENABLEMENT_FOR_CANONICAL_ONLY")
    print("NG_LONG=ALLOWED")
    print("NG_SHORT=BLOCKED")
    print()
    print("VERDICT=ENERGY_DIRECTION_POLICY_STATUS_RECORDED")
    print("ENERGY_DIRECTION_POLICY_STATUS_V1_OK")


if __name__ == "__main__":
    main()
