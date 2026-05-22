from __future__ import annotations

import argparse

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.runtime.strategy_promotion_engine_repository import (
    StrategyPromotionEngineRepository,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol")
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--apply-lifecycle", action="store_true")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    repo = StrategyPromotionEngineRepository(build_psycopg_url())

    if args.migrate or args.save or args.apply_lifecycle:
        repo.migrate()

    items = repo.build(symbol=args.symbol)

    saved = 0
    applied = 0

    if args.save:
        saved = repo.save(items)

    if args.apply_lifecycle:
        applied = repo.apply_to_lifecycle(items)

    for item in items[: args.limit]:
        print(
            "STRATEGY_PROMOTION_ENGINE_V1 "
            f"symbol={item.symbol} "
            f"strategy={item.strategy} "
            f"timeframe={item.timeframe} "
            f"source={item.trade_source} "
            f"decision={item.decision} "
            f"target_state={item.target_lifecycle_state} "
            f"runtime={item.allow_runtime} "
            f"radar={item.allow_radar} "
            f"research={item.allow_research} "
            f"reason={item.reason}",
            flush=True,
        )

    print(
        "STRATEGY_PROMOTION_ENGINE_V1_SUMMARY "
        f"total={len(items)} saved={saved} applied={applied}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
