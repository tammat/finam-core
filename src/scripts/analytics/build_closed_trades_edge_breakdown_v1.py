#!/usr/bin/env python3
# Разложение качества closed_trades по strategy/timeframe/side/session/exit_reason.

from __future__ import annotations

import argparse
import os
import psycopg2


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--symbols", required=True)
    p.add_argument("--source", default="closed_trade_engine_v1_1")
    p.add_argument("--trade-source", default="paper")
    return p.parse_args()


def conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(dsn)


def main():
    args = parse_args()
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]

    sql = """
        select
          symbol,
          strategy,
          timeframe,
          side,
          coalesce(payload->'entry_payload'->>'session_bucket', 'UNKNOWN') as session_bucket,
          coalesce(payload->'exit_payload'->>'exit_reason', 'UNKNOWN') as exit_reason,
          count(*) as trades,
          sum(case when net_pnl > 0 then 1 else 0 end) as wins,
          sum(case when net_pnl < 0 then 1 else 0 end) as losses,
          sum(net_pnl) as net_pnl,
          avg(net_pnl) as avg_pnl,
          percentile_cont(0.5) within group (order by net_pnl) as median_pnl,
          sum(case when net_pnl > 0 then net_pnl else 0 end) as gross_profit,
          abs(sum(case when net_pnl < 0 then net_pnl else 0 end)) as gross_loss,
          avg(holding_seconds) as avg_hold_seconds
        from closed_trades
        where symbol = any(%s)
          and source = %s
          and trade_source = %s
        group by symbol, strategy, timeframe, side, session_bucket, exit_reason
        order by symbol, net_pnl asc;
    """

    print("=== CLOSED TRADES EDGE BREAKDOWN V1 ===")
    print(f"symbols={','.join(symbols)}")
    print(f"source={args.source}")
    print(f"trade_source={args.trade_source}")
    print()

    with conn() as c:
        with c.cursor() as cur:
            cur.execute(sql, (symbols, args.source, args.trade_source))
            rows = cur.fetchall()

            if not rows:
                print("VERDICT=NO_ROWS")
                return

            for r in rows:
                (
                    symbol, strategy, timeframe, side, session_bucket, exit_reason,
                    trades, wins, losses, net_pnl, avg_pnl, median_pnl,
                    gross_profit, gross_loss, avg_hold_seconds
                ) = r

                pf = None
                if gross_loss and float(gross_loss) != 0.0:
                    pf = float(gross_profit or 0) / float(gross_loss)

                winrate = float(wins or 0) / float(trades or 1)

                print(
                    "EDGE_ROW "
                    f"symbol={symbol} strategy={strategy} timeframe={timeframe} side={side} "
                    f"session={session_bucket} exit_reason={exit_reason} "
                    f"trades={trades} wins={wins or 0} losses={losses or 0} "
                    f"winrate={winrate:.4f} net_pnl={float(net_pnl or 0):.8f} "
                    f"avg_pnl={float(avg_pnl or 0):.8f} median_pnl={float(median_pnl or 0):.8f} "
                    f"profit_factor={pf if pf is not None else 'None'} "
                    f"avg_hold_seconds={float(avg_hold_seconds or 0):.2f}"
                )

    print()
    print("VERDICT=OK")


if __name__ == "__main__":
    main()
