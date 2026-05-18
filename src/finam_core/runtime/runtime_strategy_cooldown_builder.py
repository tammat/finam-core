from __future__ import annotations

from datetime import date
from typing import Any


class RuntimeStrategyCooldownBuilder:
    """Русский комментарий: создаёт cooldown rules из strategy_rank_decisions."""

    COOLDOWN_RULES = {
        "DISABLE": "24 hours",
        "REDUCE": "12 hours",
    }

    def __init__(self, pg_logger: Any) -> None:
        self.pg_logger = pg_logger

    def build(self, trade_date: date) -> int:
        sql = """
        with ranked as (
            select
                strategy,
                symbol,
                timeframe,
                decision,
                reason
            from strategy_rank_decisions
            where trade_date = %s
              and decision in ('DISABLE', 'REDUCE')
        )
        insert into strategy_cooldowns (
            strategy,
            symbol,
            timeframe,
            decision,
            reason,
            cooldown_until,
            created_at,
            updated_at
        )
        select
            strategy,
            symbol,
            timeframe,
            decision,
            reason,
            now()
                + case
                    when decision = 'DISABLE'
                        then interval '24 hours'
                    when decision = 'REDUCE'
                        then interval '12 hours'
                    else interval '1 hour'
                  end,
            now(),
            now()
        from ranked
        on conflict (strategy, symbol, timeframe)
        do update set
            decision = excluded.decision,
            reason = excluded.reason,
            cooldown_until = excluded.cooldown_until,
            updated_at = now();
        """

        with self.pg_logger._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (trade_date,))
                affected = cur.rowcount
            conn.commit()

        print(
            f"RUNTIME_STRATEGY_COOLDOWNS_OK affected={affected}",
            flush=True,
        )

        return int(affected or 0)
