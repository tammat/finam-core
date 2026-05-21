from __future__ import annotations

import argparse

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.portfolio.portfolio_intelligence_repository import (
    PortfolioIntelligenceRepository,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cash", type=float, default=0.0)
    parser.add_argument("--limit", type=int, default=30)
    args = parser.parse_args()

    repo = PortfolioIntelligenceRepository(build_psycopg_url())
    snapshot = repo.build_snapshot(cash=args.cash)

    print(
        "PORTFOLIO_INTELLIGENCE_SNAPSHOT_OK "
        f"symbols={len(snapshot.symbols)} "
        f"total_equity={snapshot.total_equity} "
        f"total_exposure={snapshot.total_exposure} "
        f"total_heat={snapshot.total_heat} "
        f"total_unrealized_pnl={snapshot.total_unrealized_pnl} "
        f"total_realized_pnl={snapshot.total_realized_pnl}",
        flush=True,
    )

    for item in snapshot.symbols[: args.limit]:
        print(
            "PORTFOLIO_SYMBOL_STATE "
            f"symbol={item.symbol} "
            f"strategy={item.strategy} "
            f"regime={item.regime} "
            f"qty={item.qty} "
            f"avg_price={item.avg_price} "
            f"current_price={item.current_price} "
            f"exposure={item.exposure} "
            f"weight={item.portfolio_weight} "
            f"unrealized_pnl={item.unrealized_pnl} "
            f"realized_pnl={item.realized_pnl} "
            f"health={item.strategy_health}",
            flush=True,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
