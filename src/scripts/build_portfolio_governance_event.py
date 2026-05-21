from __future__ import annotations

import argparse

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.analytics.symbol_strategy_resolver import SymbolStrategyResolver
from finam_core.runtime.portfolio_governance_advisor import PortfolioGovernanceAdvisor
from finam_core.runtime.portfolio_governance_repository import PortfolioGovernanceRepository


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--save", action="store_true")

    args = parser.parse_args()

    database_url = build_psycopg_url()
    strategy = SymbolStrategyResolver(database_url).resolve(args.symbol)

    advisor = PortfolioGovernanceAdvisor(database_url)
    decision = advisor.build(
        symbol=args.symbol,
        strategy=strategy,
        timeframe=args.timeframe,
    )

    if args.migrate or args.save:
        repo = PortfolioGovernanceRepository(database_url)
        repo.migrate()

    if args.save:
        repo.save(
            timeframe=args.timeframe,
            decision=decision,
        )

    print(
        "PORTFOLIO_GOVERNANCE_EVENT "
        f"symbol={decision.symbol} "
        f"strategy={decision.strategy} "
        f"timeframe={args.timeframe} "
        f"heat_status={decision.portfolio_heat_status} "
        f"risk_multiplier={decision.portfolio_risk_multiplier} "
        f"exit_policy={decision.exit_policy} "
        f"allow_new_entries={decision.allow_new_entries} "
        f"mode={decision.governance_mode}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
