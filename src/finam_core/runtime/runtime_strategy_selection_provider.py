from __future__ import annotations

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


class RuntimeStrategySelectionProvider:
    """
    Русский комментарий:
    Read-only provider для RuntimeExecutionEngine.
    Читает runtime_strategy_selection и решает, можно ли запускать strategy-worker.
    """

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or build_psycopg_url()

    def get_mode(
        self,
        *,
        symbol: str,
        strategy: str,
        timeframe: str,
    ) -> str:
        sql = """
        SELECT mode
        FROM runtime_strategy_selection
        WHERE symbol = %s
          AND strategy = %s
          AND timeframe = %s
        ORDER BY updated_at DESC
        LIMIT 1
        """

        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (symbol, strategy, timeframe))
                    row = cur.fetchone()
        except Exception:
            return "UNKNOWN"

        if not row:
            return "UNKNOWN"

        return str(row[0] or "UNKNOWN")

    def allow_worker(
        self,
        *,
        symbol: str,
        strategy: str,
        timeframe: str,
    ) -> bool:
        mode = self.get_mode(
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
        )

        return mode == "PAPER_ENABLED"
