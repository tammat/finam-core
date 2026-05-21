from __future__ import annotations

import psycopg

from finam_core.portfolio.portfolio_heat_engine import PortfolioHeatDecision


class PortfolioHeatRepository:
    """
    Русский комментарий:
    Persistence для Portfolio Heat Engine.
    Только сохраняет события heat decision.
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS portfolio_heat_events (
            id BIGSERIAL PRIMARY KEY,
            symbols_count INTEGER NOT NULL,
            total_equity NUMERIC NOT NULL,
            total_exposure NUMERIC NOT NULL,
            total_unrealized_pnl NUMERIC NOT NULL,
            total_realized_pnl NUMERIC NOT NULL,
            heat NUMERIC NOT NULL,
            status TEXT NOT NULL,
            risk_multiplier NUMERIC NOT NULL,
            allow_new_entries BOOLEAN NOT NULL,
            reason TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_portfolio_heat_events_created_at
        ON portfolio_heat_events(created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_portfolio_heat_events_status
        ON portfolio_heat_events(status);
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def save(
        self,
        *,
        symbols_count: int,
        total_equity: float,
        total_exposure: float,
        total_unrealized_pnl: float,
        total_realized_pnl: float,
        decision: PortfolioHeatDecision,
    ) -> None:
        sql = """
        INSERT INTO portfolio_heat_events (
            symbols_count,
            total_equity,
            total_exposure,
            total_unrealized_pnl,
            total_realized_pnl,
            heat,
            status,
            risk_multiplier,
            allow_new_entries,
            reason
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        )
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        symbols_count,
                        total_equity,
                        total_exposure,
                        total_unrealized_pnl,
                        total_realized_pnl,
                        decision.heat,
                        decision.status,
                        decision.risk_multiplier,
                        decision.allow_new_entries,
                        decision.reason,
                    ),
                )
            conn.commit()
