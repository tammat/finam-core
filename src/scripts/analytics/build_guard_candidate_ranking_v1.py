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
            total_net_pnl / nullif(total_trades, 0) as expectancy,
            stop_trades,
            stop_net_pnl,
            take_trades,
            take_net_pnl,
            stop_trades::float8 / nullif(total_trades, 0) as stop_rate,
            take_trades::float8 / nullif(total_trades, 0) as take_rate,
            case
                when abs(stop_net_pnl) > 0 then take_net_pnl / abs(stop_net_pnl)
                else null
            end as profit_factor_proxy
        from strategy_session_exit_guard_state
    """

    with conn() as c:
        with c.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    print("=== GUARD CANDIDATE RANKING V1 ===")
    print(f"rows={len(rows)}")
    print()

    def line(prefix, r):
        (
            symbol, strategy, timeframe, side, session, decision,
            total_trades, total_net_pnl, expectancy,
            stop_trades, stop_net_pnl, take_trades, take_net_pnl,
            stop_rate, take_rate, pf
        ) = r

        print(
            f"{prefix} symbol={symbol} strategy={strategy} timeframe={timeframe} "
            f"side={side} session={session} decision={decision} "
            f"trades={total_trades} net_pnl={float(total_net_pnl or 0):.8f} "
            f"expectancy={float(expectancy or 0):.8f} "
            f"stop_trades={stop_trades} stop_rate={float(stop_rate or 0):.4f} "
            f"stop_net_pnl={float(stop_net_pnl or 0):.8f} "
            f"take_trades={take_trades} take_rate={float(take_rate or 0):.4f} "
            f"take_net_pnl={float(take_net_pnl or 0):.8f} "
            f"pf_proxy={float(pf):.4f}" if pf is not None else
            f"{prefix} symbol={symbol} strategy={strategy} timeframe={timeframe} "
            f"side={side} session={session} decision={decision} "
            f"trades={total_trades} net_pnl={float(total_net_pnl or 0):.8f} "
            f"expectancy={float(expectancy or 0):.8f} "
            f"stop_trades={stop_trades} stop_rate={float(stop_rate or 0):.4f} "
            f"stop_net_pnl={float(stop_net_pnl or 0):.8f} "
            f"take_trades={take_trades} take_rate={float(take_rate or 0):.4f} "
            f"take_net_pnl={float(take_net_pnl or 0):.8f} "
            f"pf_proxy=None"
        )

    print("WORST_BY_NET_PNL")
    for r in sorted(rows, key=lambda x: float(x[7] or 0))[:10]:
        line("WORST_ROW", r)

    print()
    print("WORST_BY_EXPECTANCY_MIN3")
    rows_min3 = [r for r in rows if int(r[6] or 0) >= 3]
    for r in sorted(rows_min3, key=lambda x: float(x[8] or 0))[:10]:
        line("WORST_EXPECTANCY_ROW", r)

    print()
    print("WORST_STOP_DOMINATION_MIN3")
    for r in sorted(rows_min3, key=lambda x: (float(x[13] or 0), float(x[10] or 0)))[:10]:
        line("STOP_DOMINATED_ROW", r)

    print()
    print("BEST_BY_NET_PNL")
    for r in sorted(rows, key=lambda x: float(x[7] or 0), reverse=True)[:10]:
        line("BEST_ROW", r)

    print()
    print("BEST_BY_EXPECTANCY_MIN3")
    for r in sorted(rows_min3, key=lambda x: float(x[8] or 0), reverse=True)[:10]:
        line("BEST_EXPECTANCY_ROW", r)

    print()
    print("VERDICT=OK")


if __name__ == "__main__":
    main()
