from __future__ import annotations

from datetime import date
from typing import Any


class RuntimeStrategyGateProvider:
    """Русский комментарий: soft-gate для runtime на основании strategy_rank_decisions."""

    BLOCKING_DECISIONS = {"DISABLE"}

    def __init__(self, pg_logger: Any) -> None:
        self.pg_logger = pg_logger

    def allows(
        self,
        *,
        trade_date: date,
        strategy: str,
        symbol: str,
        timeframe: str = "unknown",
    ) -> tuple[bool, str]:
        sql = """
        select decision, reason
        from strategy_rank_decisions
        where trade_date = %s
          and strategy = %s
          and symbol = %s
          and timeframe = %s
        limit 1
        """

        with self.pg_logger._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (trade_date, strategy, symbol, timeframe))
                row = cur.fetchone()

        if row is None:
            return True, "runtime_strategy_gate_no_rank_decision"

        decision = str(row[0]).upper()
        reason = str(row[1] or "") if len(row) > 1 else ""

        if decision in self.BLOCKING_DECISIONS:
            return False, f"runtime_strategy_gate_blocked:{decision}:{reason}"

        return True, f"runtime_strategy_gate_allowed:{decision}:{reason}"
