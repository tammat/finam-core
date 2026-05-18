from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PortfolioAwareDecision:
    allowed: bool
    reason: str


class PortfolioAwareSignalFilter:
    """Русский комментарий: блокирует новые ALERT при уже существующем риске по инструменту/портфелю."""

    def __init__(self, conn: Any):
        self.conn = conn

    def check(
        self,
        *,
        symbol: str,
        max_active_signals: int = 5,
    ) -> PortfolioAwareDecision:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                select count(*)
                from signal_lifecycle
                where symbol = %s
                  and state in ('NEW','ACTIVE','TRIGGERED')
                """,
                (symbol,),
            )
            symbol_active = int(cur.fetchone()[0] or 0)

            if symbol_active > 0:
                return PortfolioAwareDecision(
                    allowed=False,
                    reason=f"уже есть активный сигнал по инструменту; active={symbol_active}",
                )

            cur.execute(
                """
                select count(*)
                from signal_lifecycle
                where state in ('NEW','ACTIVE','TRIGGERED')
                """
            )
            total_active = int(cur.fetchone()[0] or 0)

            if total_active >= max_active_signals:
                return PortfolioAwareDecision(
                    allowed=False,
                    reason=f"достигнут лимит активных сигналов; active={total_active}; limit={max_active_signals}",
                )

        return PortfolioAwareDecision(
            allowed=True,
            reason="portfolio_filter_ok",
        )
