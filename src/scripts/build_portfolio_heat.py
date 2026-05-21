from __future__ import annotations

import argparse

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.portfolio.portfolio_heat_engine import evaluate_portfolio_heat
from finam_core.portfolio.portfolio_intelligence_repository import (
    PortfolioIntelligenceRepository,
)
from finam_core.portfolio.portfolio_heat_repository import PortfolioHeatRepository


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cash", type=float, default=0.0)
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    database_url = build_psycopg_url()
    repo = PortfolioIntelligenceRepository(database_url)
    snapshot = repo.build_snapshot(cash=args.cash)

    decision = evaluate_portfolio_heat(
        total_heat=snapshot.total_heat,
    )

    if args.migrate or args.save:
        heat_repo = PortfolioHeatRepository(database_url)
        heat_repo.migrate()

    if args.save:
        heat_repo.save(
            symbols_count=len(snapshot.symbols),
            total_equity=snapshot.total_equity,
            total_exposure=snapshot.total_exposure,
            total_unrealized_pnl=snapshot.total_unrealized_pnl,
            total_realized_pnl=snapshot.total_realized_pnl,
            decision=decision,
        )

    print(
        "PORTFOLIO_HEAT_DECISION "
        f"symbols={len(snapshot.symbols)} "
        f"total_equity={snapshot.total_equity} "
        f"total_exposure={snapshot.total_exposure} "
        f"heat={decision.heat} "
        f"status={decision.status} "
        f"risk_multiplier={decision.risk_multiplier} "
        f"allow_new_entries={decision.allow_new_entries} "
        f"reason={decision.reason}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
