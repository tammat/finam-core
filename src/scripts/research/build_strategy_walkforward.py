from __future__ import annotations

import argparse
import os

from finam_core.research.walkforward_repository import StrategyWalkForwardRepository


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--trade-source", default="paper")
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--min-trades", type=int, default=30)
    parser.add_argument("--embargo-minutes", type=int, default=60)
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    repo = StrategyWalkForwardRepository(os.environ["DATABASE_URL"])
    items = repo.build_for_symbol(
        symbol=args.symbol,
        trade_source=args.trade_source,
        train_ratio=args.train_ratio,
        min_trades=args.min_trades,
        embargo_minutes=args.embargo_minutes,
    )

    for item in items[:20]:
        print(
            "STRATEGY_WALKFORWARD "
            f"symbol={item.symbol} strategy={item.strategy} timeframe={item.timeframe} "
            f"regime={item.regime} train_trades={item.train_trades} test_trades={item.test_trades} "
            f"train_pf={round(item.train_pf, 4)} test_pf={round(item.test_pf, 4)} "
            f"stability={round(item.stability_score, 4)} status={item.status}",
            flush=True,
        )

    saved = repo.save(items) if args.save else 0
    print(
        "STRATEGY_WALKFORWARD_BUILD_OK "
        f"symbol={args.symbol} total={len(items)} saved={saved}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
