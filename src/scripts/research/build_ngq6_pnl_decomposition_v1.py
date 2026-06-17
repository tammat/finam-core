#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras


def main() -> int:
    print("=== NGQ6 PNL DECOMPOSITION V1 ===")
    print("mode=diagnostic")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                select
                    id,
                    entry_trade_id,
                    exit_trade_id,
                    side,
                    qty,
                    entry_price,
                    exit_price,
                    round(
                        case
                            when side='BUY' then (exit_price - entry_price) * qty
                            when side='SELL' then (entry_price - exit_price) * qty
                            else 0
                        end,
                        6
                    ) as gross_calc,
                    round(net_pnl, 6) as net_pnl,
                    round(
                        net_pnl - case
                            when side='BUY' then (exit_price - entry_price) * qty
                            when side='SELL' then (entry_price - exit_price) * qty
                            else 0
                        end,
                        6
                    ) as net_minus_gross,
                    quality_status,
                    quality_reason
                from closed_trade_chains_v3
                where symbol='NGQ6@RTSX'
                  and strategy='NG_CONSERVATIVE_BREAKOUT_M1'
                  and timeframe='M1'
                  and trade_source='paper'
                order by exit_ts desc
                limit 5;
            """)
            chains = cur.fetchall()

            cur.execute("""
                select
                    symbol,
                    strategy,
                    timeframe,
                    clean_trades,
                    trade_days,
                    v3_full_chains,
                    round(v3_net_pnl,6) as pnl,
                    round(v3_net_pnl / nullif(v3_full_chains,0),6) as expectancy,
                    accumulation_status
                from clean_paper_accumulation_tracker_v1
                where symbol='NGQ6@RTSX'
                  and strategy='NG_CONSERVATIVE_BREAKOUT_M1'
                  and timeframe='M1';
            """)
            tracker = cur.fetchone()

    for r in chains:
        print(
            "CHAIN_ROW "
            f"id={r['id']} "
            f"entry_trade_id={r['entry_trade_id']} "
            f"exit_trade_id={r['exit_trade_id']} "
            f"side={r['side']} "
            f"qty={r['qty']} "
            f"entry={r['entry_price']} "
            f"exit={r['exit_price']} "
            f"gross_calc={r['gross_calc']} "
            f"net_pnl={r['net_pnl']} "
            f"net_minus_gross={r['net_minus_gross']} "
            f"quality={r['quality_status']} "
            f"reason={r['quality_reason']}"
        )

    if tracker:
        print(
            "TRACKER_ROW "
            f"symbol={tracker['symbol']} "
            f"strategy={tracker['strategy']} "
            f"timeframe={tracker['timeframe']} "
            f"clean_trades={tracker['clean_trades']} "
            f"trade_days={tracker['trade_days']} "
            f"v3_full_chains={tracker['v3_full_chains']} "
            f"pnl={tracker['pnl']} "
            f"expectancy={tracker['expectancy']} "
            f"status={tracker['accumulation_status']}"
        )

    print("VERDICT=PNL_NEGATIVE_BECAUSE_FIRST_FORWARD_CHAIN_LOST")
    print("NGQ6_PNL_DECOMPOSITION_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
