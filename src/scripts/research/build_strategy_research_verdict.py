from __future__ import annotations

import argparse
import os

from finam_core.research.research_verdict_repository import StrategyResearchVerdictRepository


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--trade-source", default="paper")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    repo = StrategyResearchVerdictRepository(os.environ["DATABASE_URL"])
    items = repo.build_for_symbol(symbol=args.symbol, trade_source=args.trade_source)

    for item in items:
        print(
            "STRATEGY_RESEARCH_VERDICT "
            f"symbol={item.symbol} strategy={item.strategy} timeframe={item.timeframe} "
            f"regime={item.regime} verdict={item.verdict} confidence={round(item.confidence, 4)} "
            f"perf_pf={round(item.performance_pf, 4)} oos_pf={round(item.walkforward_test_pf, 4)} "
            f"regime_pf={round(item.regime_pf, 4)} reason={item.reason}",
            flush=True,
        )

    saved = repo.save(items) if args.save else 0
    print(
        "STRATEGY_RESEARCH_VERDICT_BUILD_OK "
        f"symbol={args.symbol} total={len(items)} saved={saved}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
