#!/usr/bin/env python3
# Scorecard по exit_reason: STOP / TAKE / TIME_EXIT / UNKNOWN.

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
          sum(net_pnl) as net_pnl,
          avg(net_pnl) as avg_pnl,
          sum(case when net_pnl > 0 then 1 else 0 end) as wins,
          sum(case when net_pnl < 0 then 1 else 0 end) as losses
        from closed_trades
        where symbol = any(%s)
          and source = %s
          and trade_source = %s
        group by symbol, strategy, timeframe, side, session_bucket, exit_reason
        order by net_pnl asc;
    """

    print("=== EXIT REASON SCORECARD V1 ===")
    print(f"symbols={','.join(symbols)}")
    print(f"source={args.source}")
    print(f"trade_source={args.trade_source}")
    print()

    with conn() as c:
        with c.cursor() as cur:
            cur.execute(sql, (symbols, args.source, args.trade_source))
            for row in cur.fetchall():
                symbol, strategy, timeframe, side, session, exit_reason, trades, net_pnl, avg_pnl, wins, losses = row
                status = "BLOCK_CANDIDATE" if exit_reason == "STOP" and float(net_pnl or 0) < 0 else "WATCH"
                print(
                    f"EXIT_ROW symbol={symbol} strategy={strategy} timeframe={timeframe} "
                    f"side={side} session={session} exit_reason={exit_reason} "
                    f"trades={trades} wins={wins or 0} losses={losses or 0} "
                    f"net_pnl={float(net_pnl or 0):.8f} avg_pnl={float(avg_pnl or 0):.8f} "
                    f"status={status}"
                )

    print()
    print("VERDICT=OK")


if __name__ == "__main__":
    main()
