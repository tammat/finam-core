#!/usr/bin/env python3
# Guard-кандидаты по связкам strategy/timeframe/side/session.
# Логика: если STOP-сделки в связке дают отрицательный PnL и 0 winrate,
# связка получает BLOCK_STOP_DOMINATED.

from __future__ import annotations

import argparse
import os
import psycopg2


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--symbols", required=True)
    p.add_argument("--source", default="closed_trade_engine_v1_1")
    p.add_argument("--trade-source", default="paper")
    p.add_argument("--min-stop-trades", type=int, default=3)
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
        with base as (
            select
              symbol,
              strategy,
              timeframe,
              side,
              coalesce(payload->'entry_payload'->>'session_bucket', 'UNKNOWN') as session_bucket,
              coalesce(payload->'exit_payload'->>'exit_reason', 'UNKNOWN') as exit_reason,
              net_pnl
            from closed_trades
            where symbol = any(%s)
              and source = %s
              and trade_source = %s
        )
        select
          symbol,
          strategy,
          timeframe,
          side,
          session_bucket,
          count(*) as total_trades,
          sum(net_pnl) as total_net_pnl,
          sum(case when exit_reason = 'STOP' then 1 else 0 end) as stop_trades,
          sum(case when exit_reason = 'STOP' and net_pnl > 0 then 1 else 0 end) as stop_wins,
          sum(case when exit_reason = 'STOP' and net_pnl < 0 then 1 else 0 end) as stop_losses,
          sum(case when exit_reason = 'STOP' then net_pnl else 0 end) as stop_net_pnl,
          sum(case when exit_reason = 'TAKE' then 1 else 0 end) as take_trades,
          sum(case when exit_reason = 'TAKE' then net_pnl else 0 end) as take_net_pnl
        from base
        group by symbol, strategy, timeframe, side, session_bucket
        order by stop_net_pnl asc;
    """

    print("=== STRATEGY SESSION EXIT GUARD V1 ===")
    print(f"symbols={','.join(symbols)}")
    print(f"source={args.source}")
    print(f"trade_source={args.trade_source}")
    print(f"min_stop_trades={args.min_stop_trades}")
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
                    symbol, strategy, timeframe, side, session,
                    total_trades, total_net_pnl,
                    stop_trades, stop_wins, stop_losses, stop_net_pnl,
                    take_trades, take_net_pnl
                ) = r

                stop_winrate = float(stop_wins or 0) / float(stop_trades or 1)

                if (
                    int(stop_trades or 0) >= args.min_stop_trades
                    and float(stop_net_pnl or 0) < 0
                    and float(stop_wins or 0) == 0
                ):
                    decision = "BLOCK_STOP_DOMINATED"
                elif float(total_net_pnl or 0) < 0:
                    decision = "WATCH_NEGATIVE_TOTAL"
                else:
                    decision = "ALLOW_WATCH"

                print(
                    f"GUARD_ROW symbol={symbol} strategy={strategy} timeframe={timeframe} "
                    f"side={side} session={session} "
                    f"total_trades={total_trades} total_net_pnl={float(total_net_pnl or 0):.8f} "
                    f"stop_trades={stop_trades or 0} stop_wins={stop_wins or 0} "
                    f"stop_losses={stop_losses or 0} stop_winrate={stop_winrate:.4f} "
                    f"stop_net_pnl={float(stop_net_pnl or 0):.8f} "
                    f"take_trades={take_trades or 0} take_net_pnl={float(take_net_pnl or 0):.8f} "
                    f"decision={decision}"
                )

    print()
    print("VERDICT=OK")


if __name__ == "__main__":
    main()
