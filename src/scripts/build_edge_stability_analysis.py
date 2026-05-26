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
    SELECT
        continuous_symbol,
        symbol,
        strategy,
        timeframe,
        edge_quartile,
        closed_trades,
        wins,
        losses,
        winrate,
        net_pnl,
        expectancy,
        profit_factor,
        payoff_ratio,
        first_expectancy,
        last_expectancy,
        stability_status,
        stability_reason
    FROM edge_stability_analysis_v1
    WHERE (%(continuous_symbol)s = '' OR continuous_symbol = %(continuous_symbol)s)
      AND (%(strategy)s = '' OR strategy = %(strategy)s)
      AND (%(timeframe)s = '' OR timeframe = %(timeframe)s)
      AND (%(trade_source)s = '' OR trade_source = %(trade_source)s)
    ORDER BY continuous_symbol, strategy, timeframe, edge_quartile;
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                sql,
                {
                    "continuous_symbol": args.continuous_symbol,
                    "strategy": args.strategy,
                    "timeframe": args.timeframe,
                    "trade_source": args.trade_source,
                },
            )
            rows = cur.fetchall()

    print(
        "EDGE_STABILITY_ANALYSIS_V1",
        f"rows={len(rows)}",
        flush=True,
    )

    for r in rows:
        print(
            "EDGE_STABILITY_ROW",
            f"continuous_symbol={r['continuous_symbol']}",
            f"symbol={r['symbol']}",
            f"strategy={r['strategy']}",
            f"timeframe={r['timeframe']}",
            f"quartile={r['edge_quartile']}",
            f"closed={r['closed_trades']}",
            f"wins={r['wins']}",
            f"losses={r['losses']}",
            f"winrate={r['winrate']}",
            f"net_pnl={r['net_pnl']}",
            f"expectancy={r['expectancy']}",
            f"first_expectancy={r['first_expectancy']}",
            f"last_expectancy={r['last_expectancy']}",
            f"status={r['stability_status']}",
            f"reason={r['stability_reason']}",
            flush=True,
        )


if __name__ == "__main__":
    main()
