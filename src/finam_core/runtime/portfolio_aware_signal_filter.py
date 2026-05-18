from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PortfolioAwareDecision:
    allowed: bool
    reason: str


class PortfolioAwareSignalFilter:
    """Русский комментарий: блокирует ALERT при уже существующем риске по инструменту/портфелю."""

    def __init__(self, conn: Any):
        self.conn = conn

    def check(
        self,
        *,
        symbol: str,
        max_active_signals: int = 5,
        check_real_positions: bool = True,
    ) -> PortfolioAwareDecision:
        with self.conn.cursor() as cur:
            if check_real_positions:
                cur.execute(
                    """
                    select count(*)
                    from real_portfolio_positions
                    where symbol = %s
                      and coalesce(qty, 0) <> 0
                    """,
                    (symbol,),
                )
                real_positions = int(cur.fetchone()[0] or 0)
                if real_positions > 0:
                    return PortfolioAwareDecision(
                        allowed=False,
                        reason=f"уже есть реальная позиция по инструменту; positions={real_positions}",
                    )

                cur.execute(
                    """
                    select count(*)
                    from managed_positions
                    where symbol = %s
                      and coalesce(qty, 0) <> 0
                    """,
                    (symbol,),
                )
                managed_positions = int(cur.fetchone()[0] or 0)
                if managed_positions > 0:
                    return PortfolioAwareDecision(
                        allowed=False,
                        reason=f"уже есть managed position по инструменту; positions={managed_positions}",
                    )

                cur.execute(
                    """
                    select count(*)
                    from position_lifecycle_state
                    where symbol = %s
                      and coalesce(remaining_qty, initial_qty, 0) <> 0
                    """,
                    (symbol,),
                )
                lifecycle_positions = int(cur.fetchone()[0] or 0)
                if lifecycle_positions > 0:
                    return PortfolioAwareDecision(
                        allowed=False,
                        reason=f"уже есть lifecycle position по инструменту; positions={lifecycle_positions}",
                    )

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
