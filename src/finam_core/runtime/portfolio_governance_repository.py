from __future__ import annotations

import psycopg

from finam_core.runtime.portfolio_governance_advisor import PortfolioGovernanceDecision


class PortfolioGovernanceRepository:
    """
    Русский комментарий:
    Persistence для итоговых portfolio governance advisory decisions.
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS portfolio_governance_events (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            portfolio_heat_status TEXT NOT NULL,
            portfolio_risk_multiplier NUMERIC NOT NULL,
            exit_policy TEXT,
            allow_new_entries BOOLEAN NOT NULL,
            governance_mode TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_portfolio_governance_events_created_at
        ON portfolio_governance_events(created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_portfolio_governance_events_symbol
        ON portfolio_governance_events(symbol, strategy, timeframe);

        CREATE INDEX IF NOT EXISTS idx_portfolio_governance_events_heat
        ON portfolio_governance_events(portfolio_heat_status);
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def save(self, *, timeframe: str, decision: PortfolioGovernanceDecision) -> None:
        sql = """
        INSERT INTO portfolio_governance_events (
            symbol,
            strategy,
            timeframe,
            portfolio_heat_status,
            portfolio_risk_multiplier,
            exit_policy,
            allow_new_entries,
            governance_mode
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        decision.symbol,
                        decision.strategy,
                        timeframe,
                        decision.portfolio_heat_status,
                        decision.portfolio_risk_multiplier,
                        decision.exit_policy,
                        decision.allow_new_entries,
                        decision.governance_mode,
                    ),
                )
            conn.commit()
