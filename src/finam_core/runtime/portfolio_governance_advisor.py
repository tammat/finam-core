from __future__ import annotations

from dataclasses import dataclass

from finam_core.runtime.portfolio_heat_advisor import (
    RuntimePortfolioHeatAdvisor,
)
from finam_core.runtime.exit_policy_advisor import (
    RuntimeExitPolicyAdvisor,
)


@dataclass(frozen=True)
class PortfolioGovernanceDecision:
    symbol: str
    strategy: str

    portfolio_heat_status: str
    portfolio_risk_multiplier: float

    exit_policy: str | None

    governance_mode: str
    allow_new_entries: bool


class PortfolioGovernanceAdvisor:
    """
    Русский комментарий:
    Unified governance advisory layer.

    Только advisory.
    Не меняет:
      - execution
      - risk
      - positions
      - orders
    """

    def __init__(self, database_url: str):
        self.database_url = database_url

        self.heat = RuntimePortfolioHeatAdvisor(database_url)
        self.exit_policy = RuntimeExitPolicyAdvisor(database_url)

    def build(
        self,
        *,
        symbol: str,
        strategy: str,
        timeframe: str,
    ) -> PortfolioGovernanceDecision:

        heat = self.heat.get_latest_advice()

        policy = self.exit_policy.get_advice(
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
        )

        return PortfolioGovernanceDecision(
            symbol=symbol,
            strategy=strategy,

            portfolio_heat_status=(
                heat.status if heat else "UNKNOWN"
            ),

            portfolio_risk_multiplier=(
                heat.risk_multiplier if heat else 1.0
            ),

            exit_policy=(
                policy.policy
                if policy is not None
                else None
            ),

            governance_mode="ADVISORY_ONLY",

            allow_new_entries=(
                heat.allow_new_entries
                if heat
                else True
            ),
        )
