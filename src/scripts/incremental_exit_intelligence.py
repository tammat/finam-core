from __future__ import annotations

import argparse
import psycopg

from finam_core.analytics.incremental_exit_intelligence import (
    IncrementalExitInput,
    build_incremental_exit_advice,
)
from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.analytics.symbol_strategy_resolver import SymbolStrategyResolver


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--current-price", type=float, required=True)
    args = parser.parse_args()

    database_url = build_psycopg_url()
    strategy = SymbolStrategyResolver(database_url).resolve(args.symbol)

    sql = """
    SELECT
        selected_policy,
        take_distance,
        stop_distance
    FROM analytics_exit_policy_selected
    WHERE symbol = %s
      AND strategy = %s
      AND timeframe = %s
      AND is_active = TRUE
    ORDER BY selected_at DESC
    LIMIT 1
    """

    trade_sql = """
    SELECT side, price, qty
    FROM trades
    WHERE symbol = %s
      AND (
          payload->>'paper_only' = 'true'
          OR trade_source ILIKE '%%paper%%'
          OR origin ILIKE '%%paper%%'
      )
    ORDER BY id DESC
    LIMIT 1
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (args.symbol, strategy, args.timeframe))
            policy = cur.fetchone()

            if not policy:
                print(
                    "INCREMENTAL_EXIT_ADVICE_EMPTY "
                    f"symbol={args.symbol} strategy={strategy} timeframe={args.timeframe} "
                    "reason=no_active_exit_policy",
                    flush=True,
                )
                return 0

            cur.execute(trade_sql, (args.symbol,))
            trade = cur.fetchone()

            if not trade:
                print(
                    "INCREMENTAL_EXIT_ADVICE_EMPTY "
                    f"symbol={args.symbol} strategy={strategy} timeframe={args.timeframe} "
                    "reason=no_paper_trade",
                    flush=True,
                )
                return 0

    side = str(trade[0])
    entry_price = float(trade[1])
    qty = float(trade[2])

    advice = build_incremental_exit_advice(
        IncrementalExitInput(
            symbol=args.symbol,
            strategy=strategy,
            timeframe=args.timeframe,
            side=side,
            entry_price=entry_price,
            current_price=args.current_price,
            qty=qty,
            take_distance=float(policy[1]),
            stop_distance=float(policy[2]),
        )
    )

    print(
        "INCREMENTAL_EXIT_ADVICE "
        f"symbol={advice.symbol} "
        f"strategy={advice.strategy} "
        f"timeframe={advice.timeframe} "
        f"side={advice.side} "
        f"entry={entry_price} "
        f"current={args.current_price} "
        f"take_price={advice.take_price} "
        f"stop_price={advice.stop_price} "
        f"distance_to_take={advice.distance_to_take} "
        f"distance_to_stop={advice.distance_to_stop} "
        f"action={advice.action} "
        f"reason={advice.reason}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
