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
        """
        Русский комментарий:
        Основной источник истины — strategy_lifecycle_state.
        Fallback — runtime_strategy_selection для обратной совместимости.
        """
        lifecycle_mode = self._get_lifecycle_mode(
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
        )

        if lifecycle_mode != "UNKNOWN":
            return lifecycle_mode

        return self._get_legacy_mode(
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
        )

    def _get_lifecycle_mode(
        self,
        *,
        symbol: str,
        strategy: str,
        timeframe: str,
    ) -> str:
        sql = """
        SELECT lifecycle_state
        FROM strategy_lifecycle_state
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

    def _get_legacy_mode(
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
        sql = """
        SELECT lifecycle_state, allow_runtime
        FROM strategy_lifecycle_state
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
            row = None

        if row is not None:
            return str(row[0] or "").upper() == "PAPER" and bool(row[1])

        mode = self.get_mode(
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
        )

        return mode == "PAPER_ENABLED"
