from __future__ import annotations

from dataclasses import dataclass

import psycopg


@dataclass(frozen=True)
class PortfolioHeatAdvice:
    status: str
    heat: float
    risk_multiplier: float
    allow_new_entries: bool
    reason: str
    source: str = "portfolio_heat_events"


class RuntimePortfolioHeatAdvisor:
    """
    Русский комментарий:
    Runtime Governance advisory-layer.

    Только читает последнее portfolio_heat_events.
    Не меняет RiskStack, execution и заявки.
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def get_latest_advice(self) -> PortfolioHeatAdvice | None:
        sql = """
        SELECT
            status,
            heat,
            risk_multiplier,
            allow_new_entries,
            reason
        FROM portfolio_heat_events
        ORDER BY created_at DESC
        LIMIT 1
        """

        try:
            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    row = cur.fetchone()
        except Exception:
            return None

        if row is None:
            return None

        return PortfolioHeatAdvice(
            status=str(row[0]),
            heat=float(row[1]),
            risk_multiplier=float(row[2]),
            allow_new_entries=bool(row[3]),
            reason=str(row[4]),
        )
