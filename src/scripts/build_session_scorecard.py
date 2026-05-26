#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import psycopg
from psycopg.rows import dict_row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--continuous-symbol", default="")
    parser.add_argument("--strategy", default="")
    parser.add_argument("--timeframe", default="")
    parser.add_argument("--trade-source", default="paper")
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set")

    sql = """
    SELECT session_bucket, hour_utc, closed_trades, wins, losses, winrate,
           net_pnl, expectancy, profit_factor, session_edge_status
    FROM session_scorecard_v1
    WHERE (%(continuous_symbol)s = '' OR continuous_symbol = %(continuous_symbol)s)
      AND (%(strategy)s = '' OR strategy = %(strategy)s)
      AND (%(timeframe)s = '' OR timeframe = %(timeframe)s)
      AND (%(trade_source)s = '' OR trade_source = %(trade_source)s)
    ORDER BY session_bucket, hour_utc;
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, vars(args).replace("-", "_") if False else {
                "continuous_symbol": args.continuous_symbol,
                "strategy": args.strategy,
                "timeframe": args.timeframe,
                "trade_source": args.trade_source,
            })
            rows = cur.fetchall()

    print("SESSION_SCORECARD_V1", f"rows={len(rows)}", flush=True)
    for r in rows:
        print(
            "SESSION_ROW",
            f"session={r['session_bucket']}",
            f"hour_utc={r['hour_utc']}",
            f"closed={r['closed_trades']}",
            f"wins={r['wins']}",
            f"losses={r['losses']}",
            f"winrate={r['winrate']}",
            f"net_pnl={r['net_pnl']}",
            f"expectancy={r['expectancy']}",
            f"profit_factor={r['profit_factor']}",
            f"status={r['session_edge_status']}",
            flush=True,
        )


if __name__ == "__main__":
    main()
