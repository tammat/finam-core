#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2


def conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(dsn)


def main():
    sql = """
        select
            symbol,
            strategy,
            timeframe,
            side,
            session_bucket,
            decision,
            total_trades,
            total_net_pnl,
            stop_trades,
            stop_wins,
            stop_losses,
            stop_net_pnl,
            take_trades,
            take_net_pnl
        from strategy_session_exit_guard_state
        order by
            case decision
                when 'BLOCK_STOP_DOMINATED' then 0
                when 'WATCH_NEGATIVE_TOTAL' then 1
                else 2
            end,
            total_net_pnl asc;
    """

    print("=== RUNTIME PROBLEM AUDIT V1 ===")

    with conn() as c:
        with c.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

            critical = 0
            watch = 0
            allow = 0

            for r in rows:
                (
                    symbol, strategy, timeframe, side, session, decision,
                    total_trades, total_net_pnl,
                    stop_trades, stop_wins, stop_losses, stop_net_pnl,
                    take_trades, take_net_pnl
                ) = r

                if decision == "BLOCK_STOP_DOMINATED":
                    critical += 1
                elif decision == "WATCH_NEGATIVE_TOTAL":
                    watch += 1
                else:
                    allow += 1

                print(
                    f"AUDIT_ROW symbol={symbol} strategy={strategy} timeframe={timeframe} "
                    f"side={side} session={session} decision={decision} "
                    f"total_trades={total_trades} total_net_pnl={float(total_net_pnl):.8f} "
                    f"stop_trades={stop_trades} stop_wins={stop_wins} stop_losses={stop_losses} "
                    f"stop_net_pnl={float(stop_net_pnl):.8f} "
                    f"take_trades={take_trades} take_net_pnl={float(take_net_pnl):.8f}"
                )

            print()
            print(f"SUMMARY critical_block={critical} watch_negative={watch} allow_watch={allow}")

    print("VERDICT=OK")


if __name__ == "__main__":
    main()
