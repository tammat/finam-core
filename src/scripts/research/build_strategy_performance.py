from __future__ import annotations

import argparse
import os

from finam_core.research.strategy_performance_repository import StrategyPerformanceRepository


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--trade-source", default="paper")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    database_url = os.environ["DATABASE_URL"]
    repo = StrategyPerformanceRepository(database_url)

    items = repo.build_for_symbol(symbol=args.symbol, trade_source=args.trade_source)

    for item in items[:20]:
        print(
            "STRATEGY_PERFORMANCE "
            f"symbol={item.symbol} strategy={item.strategy} timeframe={item.timeframe} "
            f"regime={item.regime} trades={item.trades} pf={round(item.profit_factor, 4)} "
            f"expectancy={round(item.expectancy, 6)} status={item.status}",
            flush=True,
        )

    saved = repo.save(items) if args.save else 0

    print(
        "STRATEGY_PERFORMANCE_BUILD_OK "
        f"symbol={args.symbol} total={len(items)} saved={saved}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
