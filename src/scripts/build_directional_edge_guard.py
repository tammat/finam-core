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
        regime_direction,
        closed_trades,
        winrate,
        net_pnl,
        expectancy,
        directional_edge_status,
        directional_edge_reason,
        guard_mode
    FROM directional_edge_guard_v1
    WHERE (%(continuous_symbol)s = '' OR continuous_symbol = %(continuous_symbol)s)
      AND (%(strategy)s = '' OR strategy = %(strategy)s)
      AND (%(timeframe)s = '' OR timeframe = %(timeframe)s)
      AND (%(trade_source)s = '' OR trade_source = %(trade_source)s)
    ORDER BY net_pnl DESC;
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
        "DIRECTIONAL_EDGE_GUARD_V1",
        f"rows={len(rows)}",
        f"mode=analytics_only",
        flush=True,
    )

    for r in rows:
        print(
            "DIRECTIONAL_EDGE_ROW",
            f"continuous_symbol={r['continuous_symbol']}",
            f"symbol={r['symbol']}",
            f"strategy={r['strategy']}",
            f"timeframe={r['timeframe']}",
            f"regime_direction={r['regime_direction']}",
            f"closed={r['closed_trades']}",
            f"winrate={r['winrate']}",
            f"net_pnl={r['net_pnl']}",
            f"expectancy={r['expectancy']}",
            f"status={r['directional_edge_status']}",
            f"reason={r['directional_edge_reason']}",
            f"guard_mode={r['guard_mode']}",
            flush=True,
        )


if __name__ == "__main__":
    main()
