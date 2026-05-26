#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.directional_edge_guard import DirectionalEdgeGuard


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--continuous-symbol", required=True)
    parser.add_argument("--strategy", required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--side", required=True, choices=["BUY", "SELL"])
    parser.add_argument("--regime-direction", required=True)
    parser.add_argument("--trade-source", default="paper")
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set")

    sql = """
    SELECT directional_edge_status
    FROM directional_edge_guard_v1
    WHERE continuous_symbol = %(continuous_symbol)s
      AND strategy = %(strategy)s
      AND timeframe = %(timeframe)s
      AND trade_source = %(trade_source)s
      AND regime_direction = %(regime_direction)s
    LIMIT 1;
    """

    guard_status = None
    with psycopg.connect(database_url) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                sql,
                {
                    "continuous_symbol": args.continuous_symbol,
                    "strategy": args.strategy,
                    "timeframe": args.timeframe,
                    "trade_source": args.trade_source,
                    "regime_direction": args.regime_direction,
                },
            )
            row = cur.fetchone()
            if row:
                guard_status = row["directional_edge_status"]

    decision = DirectionalEdgeGuard(mode="soft_advisory").decide(
        symbol=args.symbol,
        continuous_symbol=args.continuous_symbol,
        strategy=args.strategy,
        timeframe=args.timeframe,
        side=args.side,
        regime_direction=args.regime_direction,
        guard_status=guard_status,
    )

    print(
        "DIRECTIONAL_EDGE_GUARD_V2",
        f"mode={decision.mode}",
        f"status={decision.status}",
        f"reason={decision.reason}",
        f"symbol={decision.symbol}",
        f"continuous_symbol={decision.continuous_symbol}",
        f"strategy={decision.strategy}",
        f"timeframe={decision.timeframe}",
        f"side={decision.side}",
        f"regime_direction={decision.regime_direction}",
        f"guard_status={decision.guard_status}",
        flush=True,
    )


if __name__ == "__main__":
    main()
