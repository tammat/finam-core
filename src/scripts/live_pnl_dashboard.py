# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import psycopg2


def dsn() -> str:
    return (
        os.getenv("DATABASE_URL")
        or os.getenv("POSTGRES_DSN")
        or "host=127.0.0.1 port=5432 dbname=finam user=finam password=finam"
    )


def main() -> int:
    with psycopg2.connect(dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COALESCE(SUM(realized_pnl), 0),
                    COALESCE(MIN(max_drawdown), 0),
                    COUNT(*)
                FROM portfolio_pnl_events
            """)
            total_pnl, max_dd, exits = cur.fetchone()

            cur.execute("""
                SELECT symbol, ROUND(SUM(realized_pnl)::numeric, 4) AS pnl, COUNT(*)
                FROM portfolio_pnl_events
                GROUP BY symbol
                ORDER BY pnl DESC
            """)
            by_symbol = cur.fetchall()

            cur.execute("""
                SELECT ts, symbol, realized_pnl, cumulative_pnl, max_drawdown, reason
                FROM portfolio_pnl_events
                ORDER BY id DESC
                LIMIT 10
            """)
            last = cur.fetchall()

    print("LIVE_PNL_DASHBOARD")
    print(f"exits={exits}")
    print(f"total_realized_pnl={round(float(total_pnl), 4)}")
    print(f"max_drawdown={round(float(max_dd), 4)}")

    print("\nPNL_BY_SYMBOL")
    for symbol, pnl, count in by_symbol:
        print(f"symbol={symbol} pnl={pnl} exits={count}")

    print("\nLAST_EXITS")
    for row in last:
        ts, symbol, realized, cumulative, dd, reason = row
        print(
            f"ts={ts} symbol={symbol} realized={round(float(realized), 4)} "
            f"cumulative={round(float(cumulative), 4)} dd={round(float(dd), 4)} reason={reason}"
        )

    print("STATUS=OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
