from __future__ import annotations

import argparse

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.analytics.strategy_ranking_v2_repository import StrategyRankingV2Repository


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol")
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()

    repo = StrategyRankingV2Repository(build_psycopg_url())

    if args.migrate or args.save:
        repo.migrate()

    items = repo.build(symbol=args.symbol)

    saved = 0
    if args.save:
        saved = repo.save(items)

    for item in items[: args.limit]:
        print(
            "STRATEGY_RANKING_V2 "
            f"symbol={item.symbol} "
            f"strategy={item.strategy} "
            f"timeframe={item.timeframe} "
            f"source={item.trade_source} "
            f"score={item.score} "
            f"status={item.rank_status} "
            f"reason={item.reason}",
            flush=True,
        )

    print(
        "STRATEGY_RANKING_V2_SUMMARY "
        f"total={len(items)} saved={saved}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
