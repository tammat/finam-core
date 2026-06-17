#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras


def main() -> int:
    print("=== NGQ6 FORWARD EXIT MONITOR V1 ===")
    print("mode=diagnostic")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                select
                    id,
                    created_at,
                    side,
                    strategy,
                    timeframe,
                    origin,
                    trade_source,
                    qty,
                    price
                from trades
                where symbol='NGQ6@RTSX'
                  and coalesce(trade_source,'')='paper'
                  and coalesce(origin,'paper')='paper'
                  and strategy='NG_CONSERVATIVE_BREAKOUT_M1'
                  and timeframe='M1'
                  and created_at >= now() - interval '24 hours'
                order by created_at;
            """)
            trades = cur.fetchall()

            cur.execute("""
                select
                    coalesce(sum(
                        case
                            when side='BUY' then qty
                            when side='SELL' then -qty
                            else 0
                        end
                    ),0) as net_qty,
                    count(*) filter (where side='BUY') as buys,
                    count(*) filter (where side='SELL') as sells
                from trades
                where symbol='NGQ6@RTSX'
                  and coalesce(trade_source,'')='paper'
                  and coalesce(origin,'paper')='paper'
                  and strategy='NG_CONSERVATIVE_BREAKOUT_M1'
                  and timeframe='M1'
                  and created_at >= now() - interval '24 hours';
            """)
            state = cur.fetchone()

            cur.execute("""
                select
                    count(*) as bad_identity_rows
                from trades
                where symbol='NGQ6@RTSX'
                  and coalesce(trade_source,'')='paper'
                  and coalesce(origin,'paper')='paper'
                  and (
                       coalesce(strategy,'') in ('', 'UNKNOWN', 'UNKNOWN_STRATEGY')
                    or coalesce(timeframe,'') in ('', 'LIVE', 'UNKNOWN', 'UNKNOWN_TIMEFRAME')
                  );
            """)
            bad = cur.fetchone()

            cur.execute("""
                select
                    symbol,
                    strategy,
                    timeframe,
                    clean_trades,
                    trade_days,
                    v3_full_chains,
                    v3_partial_chains,
                    round(v3_net_pnl,6) as pnl,
                    accumulation_status
                from clean_paper_accumulation_tracker_v1
                where symbol='NGQ6@RTSX'
                  and strategy='NG_CONSERVATIVE_BREAKOUT_M1'
                  and timeframe='M1';
            """)
            tracker = cur.fetchone()

    for r in trades:
        print(
            "TRADE_ROW "
            f"id={r['id']} "
            f"created_at={r['created_at']} "
            f"side={r['side']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"origin={r['origin']} "
            f"trade_source={r['trade_source']} "
            f"qty={r['qty']} "
            f"price={r['price']}"
        )

    buys = int(state["buys"] or 0)
    sells = int(state["sells"] or 0)
    net_qty = float(state["net_qty"] or 0)
    bad_rows = int(bad["bad_identity_rows"] or 0)

    print(
        "NGQ6_FORWARD_STATE "
        f"buys_24h={buys} "
        f"sells_24h={sells} "
        f"net_qty_24h={net_qty} "
        f"bad_identity_rows={bad_rows}"
    )

    if tracker:
        print(
            "NGQ6_V3_STATE "
            f"clean_trades={tracker['clean_trades']} "
            f"trade_days={tracker['trade_days']} "
            f"v3_full_chains={tracker['v3_full_chains']} "
            f"v3_partial_chains={tracker['v3_partial_chains']} "
            f"pnl={tracker['pnl']} "
            f"status={tracker['accumulation_status']}"
        )

    if bad_rows != 0:
        verdict = "BAD_IDENTITY_ROWS_REMAIN"
    elif buys > 0 and sells == 0:
        verdict = "WAITING_FOR_FORWARD_EXIT"
    elif buys > 0 and sells > 0 and abs(net_qty) < 1e-9:
        verdict = "FORWARD_EXIT_READY_FOR_V3_REBUILD"
    elif buys > 0 and sells > 0 and abs(net_qty) >= 1e-9:
        verdict = "PARTIAL_EXIT_OR_POSITION_STILL_OPEN"
    else:
        verdict = "NO_FORWARD_POSITION_FOUND"

    print(f"VERDICT={verdict}")
    print("NGQ6_FORWARD_EXIT_MONITOR_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
