#!/usr/bin/env python3
import argparse
import os

import psycopg
from psycopg.rows import dict_row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--continuous-symbol", default="")
    parser.add_argument("--symbol", default="")
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
        trade_source,
        closed_trades,
        wins,
        losses,
        flats,
        winrate,
        net_pnl,
        expectancy,
        avg_win,
        avg_loss,
        profit_factor,
        payoff_ratio,
        avg_holding_minutes,
        first_entry_ts,
        last_exit_ts
    FROM strategy_scorecard_v1
    WHERE (%(continuous_symbol)s = '' OR continuous_symbol = %(continuous_symbol)s)
      AND (%(symbol)s = '' OR symbol = %(symbol)s)
      AND (%(strategy)s = '' OR strategy = %(strategy)s)
      AND (%(timeframe)s = '' OR timeframe = %(timeframe)s)
      AND (%(trade_source)s = '' OR trade_source = %(trade_source)s)
    ORDER BY closed_trades DESC, net_pnl DESC;
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                sql,
                {
                    "continuous_symbol": args.continuous_symbol,
                    "symbol": args.symbol,
                    "strategy": args.strategy,
                    "timeframe": args.timeframe,
                    "trade_source": args.trade_source,
                },
            )
            rows = cur.fetchall()

    print(
        "STRATEGY_SCORECARD_V1",
        f"continuous_symbol={args.continuous_symbol or 'ALL'}",
        f"symbol={args.symbol or 'ALL'}",
        f"strategy={args.strategy or 'ALL'}",
        f"timeframe={args.timeframe or 'ALL'}",
        f"rows={len(rows)}",
        flush=True,
    )

    for r in rows:
        print(
            "SCORECARD_ROW",
            f"continuous_symbol={r['continuous_symbol']}",
            f"symbol={r['symbol']}",
            f"strategy={r['strategy']}",
            f"timeframe={r['timeframe']}",
            f"closed={r['closed_trades']}",
            f"wins={r['wins']}",
            f"losses={r['losses']}",
            f"winrate={r['winrate']}",
            f"net_pnl={r['net_pnl']}",
            f"expectancy={r['expectancy']}",
            f"avg_win={r['avg_win']}",
            f"avg_loss={r['avg_loss']}",
            f"profit_factor={r['profit_factor']}",
            f"payoff_ratio={r['payoff_ratio']}",
            f"avg_holding_min={r['avg_holding_minutes']}",
            flush=True,
        )


if __name__ == "__main__":
    main()
