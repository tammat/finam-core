#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras


def main() -> int:
    print("=== NGQ6 FORWARD EXIT IDENTITY VERIFY V1 ===")
    print("mode=diagnostic")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                select
                    id,
                    created_at,
                    symbol,
                    strategy,
                    timeframe,
                    side,
                    origin,
                    trade_source,
                    qty,
                    price
                from trades
                where symbol='NGQ6@RTSX'
                  and coalesce(trade_source,'')='paper'
                  and coalesce(origin,'paper')='paper'
                  and created_at >= now() - interval '24 hours'
                order by created_at desc;
            """)
            recent = cur.fetchall()

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
                  and strategy='NG_CONSERVATIVE_BREAKOUT_M1'
                  and timeframe='M1'
                  and coalesce(trade_source,'')='paper'
                  and coalesce(origin,'paper')='paper'
                  and created_at >= now() - interval '24 hours';
            """)
            balance = cur.fetchone()

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

            cur.execute("""
                select
                    count(*) as chains,
                    max(exit_ts) as last_exit_ts,
                    round(coalesce(sum(net_pnl),0),6) as pnl
                from closed_trade_chains_v3
                where symbol='NGQ6@RTSX'
                  and strategy='NG_CONSERVATIVE_BREAKOUT_M1'
                  and timeframe='M1'
                  and trade_source='paper';
            """)
            chains = cur.fetchone()

    print()
    print("RECENT_NGQ6_TRADES_24H")
    for r in recent:
        print(
            "TRADE_ROW "
            f"id={r['id']} "
            f"created_at={r['created_at']} "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"side={r['side']} "
            f"origin={r['origin']} "
            f"trade_source={r['trade_source']} "
            f"qty={r['qty']} "
            f"price={r['price']}"
        )

    net_qty = float(balance["net_qty"] or 0)
    buys = int(balance["buys"] or 0)
    sells = int(balance["sells"] or 0)
    bad_rows = int(bad["bad_identity_rows"] or 0)

    print()
    print(
        "NGQ6_FORWARD_POSITION_STATE "
        f"buys_24h={buys} "
        f"sells_24h={sells} "
        f"net_qty_24h={net_qty}"
    )

    print(f"NGQ6_BAD_IDENTITY_ROWS={bad_rows}")

    if tracker:
        print(
            "NGQ6_CLEAN_V3_TRACKER "
            f"clean_trades={tracker['clean_trades']} "
            f"trade_days={tracker['trade_days']} "
            f"v3_full_chains={tracker['v3_full_chains']} "
            f"v3_partial_chains={tracker['v3_partial_chains']} "
            f"pnl={tracker['pnl']} "
            f"status={tracker['accumulation_status']}"
        )
    else:
        print("NGQ6_CLEAN_V3_TRACKER missing=1")

    print(
        "NGQ6_CHAINS_V3 "
        f"chains={chains['chains']} "
        f"last_exit_ts={chains['last_exit_ts']} "
        f"pnl={chains['pnl']}"
    )

    if bad_rows != 0:
        verdict = "BAD_IDENTITY_ROWS_REMAIN"
    elif buys > 0 and sells == 0:
        verdict = "WAITING_FOR_FORWARD_EXIT"
    elif sells > 0 and int(chains["chains"] or 0) <= 10:
        verdict = "EXIT_PRESENT_REBUILD_REQUIRED_OR_PAIRING_BLOCKED"
    elif int(chains["chains"] or 0) > 10:
        verdict = "NGQ6_FORWARD_CHAIN_ADVANCED"
    else:
        verdict = "NO_RECENT_FORWARD_POSITION"

    print(f"VERDICT={verdict}")
    print("NGQ6_FORWARD_EXIT_IDENTITY_VERIFY_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
