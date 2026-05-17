from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any


class StrategyRankWeightProvider:
    """Русский комментарий: отдаёт runtime-вес стратегии на основании strategy_rank_decisions."""

    DECISION_WEIGHTS = {
        "ENABLE": Decimal("1.00"),
        "REDUCE": Decimal("0.50"),
        "WATCH": Decimal("0.25"),
        "DISABLE": Decimal("0.00"),
    }

    def __init__(self, pg_logger: Any) -> None:
        self.pg_logger = pg_logger

    def get_weight(
        self,
        *,
        trade_date: date,
        strategy: str,
        symbol: str,
        timeframe: str = "unknown",
    ) -> Decimal:
        sql = """
        select decision
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
            return Decimal("0.25")

        decision = str(row[0]).upper()
        return self.DECISION_WEIGHTS.get(decision, Decimal("0.25"))
