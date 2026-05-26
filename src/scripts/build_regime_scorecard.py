#!/usr/bin/env python3

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
        strategy,
        timeframe,
        regime_direction,
        edge_reason,
        hour_utc,
        closed_trades,
        wins,
        losses,
        winrate,
        net_pnl,
        expectancy,
        avg_win,
        avg_loss,
        profit_factor,
        payoff_ratio,
        avg_holding_minutes
    FROM regime_scorecard_v1
    WHERE (%(continuous_symbol)s = '' OR continuous_symbol = %(continuous_symbol)s)
      AND (%(strategy)s = '' OR strategy = %(strategy)s)
      AND (%(timeframe)s = '' OR timeframe = %(timeframe)s)
      AND (%(trade_source)s = '' OR trade_source = %(trade_source)s)
    ORDER BY net_pnl DESC, closed_trades DESC;
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
        "REGIME_SCORECARD_V1",
        f"rows={len(rows)}",
        flush=True,
    )

    for r in rows:
        print(
            "REGIME_ROW",
            f"continuous_symbol={r['continuous_symbol']}",
            f"strategy={r['strategy']}",
            f"timeframe={r['timeframe']}",
            f"regime={r['regime_direction']}",
            f"edge_reason={r['edge_reason']}",
            f"hour_utc={r['hour_utc']}",
            f"closed={r['closed_trades']}",
            f"winrate={r['winrate']}",
            f"net_pnl={r['net_pnl']}",
            f"expectancy={r['expectancy']}",
            f"profit_factor={r['profit_factor']}",
            f"payoff_ratio={r['payoff_ratio']}",
            flush=True,
        )


if __name__ == "__main__":
    main()
