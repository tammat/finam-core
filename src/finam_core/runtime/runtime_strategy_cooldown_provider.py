from __future__ import annotations

from typing import Any


class RuntimeStrategyCooldownProvider:
    """Русский комментарий: проверяет, находится ли стратегия в cooldown."""

    def __init__(self, pg_logger: Any) -> None:
        self.pg_logger = pg_logger

    def allows(
        self,
        *,
        strategy: str,
        symbol: str,
        timeframe: str = "unknown",
    ) -> tuple[bool, str]:
        sql = """
        select decision, reason, cooldown_until
        from strategy_cooldowns
        where strategy = %s
          and symbol = %s
          and timeframe = %s
          and cooldown_until > now()
        limit 1
        """

        with self.pg_logger._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (strategy, symbol, timeframe))
                row = cur.fetchone()

        if row is None:
            return True, "runtime_strategy_cooldown_not_active"

        decision = str(row[0])
        reason = str(row[1])
        cooldown_until = str(row[2])

        return False, (
            f"runtime_strategy_cooldown_active:"
            f"decision={decision}:reason={reason}:until={cooldown_until}"
        )
