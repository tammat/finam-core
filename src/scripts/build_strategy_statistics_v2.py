from __future__ import annotations

import argparse

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.analytics.strategy_statistics_v2_repository import (
    StrategyStatisticsV2Repository,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    repo = StrategyStatisticsV2Repository(build_psycopg_url())

    if args.migrate or args.save:
        repo.migrate()

    items = repo.build_for_symbol(symbol=args.symbol)

    saved = 0
    if args.save:
        saved = repo.save(items)

    for item in items:
        print(
            "STRATEGY_STATISTICS_V2 "
            f"symbol={item.symbol} "
            f"strategy={item.strategy} "
            f"timeframe={item.timeframe} "
            f"source={item.trade_source} "
            f"trades={item.trades} "
            f"pf={round(item.profit_factor, 4)} "
            f"winrate={round(item.winrate, 4)} "
            f"expectancy={round(item.expectancy, 6)} "
            f"full_ctx={round(item.quality_full_ratio, 4)} "
            f"partial_ctx={round(item.quality_partial_ratio, 4)} "
            f"weak_ctx={round(item.risk_context_weak_ratio, 4)} "
            f"high_heat={round(item.high_heat_ratio, 4)} "
            f"lifecycle_problem={round(item.lifecycle_problem_ratio, 4)} "
            f"status={item.status}",
            flush=True,
        )

    print(
        "STRATEGY_STATISTICS_V2_SUMMARY "
        f"symbol={args.symbol} total={len(items)} saved={saved}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
