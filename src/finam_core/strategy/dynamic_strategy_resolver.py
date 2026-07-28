from __future__ import annotations

from typing import Any

class DynamicStrategyResolver:
    """Выбирает только явно назначенную в БД стратегию.

    Отсутствие назначения возвращает ``UNASSIGNED``. Это намеренный fail-closed:
    общий fallback больше не может незаметно превратить любой инструмент в
    ``VOLATILITY_BREAKOUT_EQUITY`` или legacy-стратегию.
    """

    def __init__(self, pg_logger: Any | None = None) -> None:
        self.pg_logger = pg_logger

    def strategy_for_symbol(self, symbol: str) -> str:
        assigned = self._strategy_from_assignment(symbol)
        if assigned:
            return assigned

        dynamic = self._strategy_from_dynamic_watchlist(symbol)
        if dynamic:
            return dynamic

        return "UNASSIGNED"

    def _strategy_from_assignment(self, symbol: str) -> str | None:
        if self.pg_logger is None:
            return None

        sql = """
        select strategy_code
        from analytics.runtime_strategy_assignment_v1
        where symbol = %s
          and enabled = true
        order by priority desc, updated_at desc
        limit 1
        """
        try:
            conn = getattr(self.pg_logger, "conn", None)
            if conn is None and hasattr(self.pg_logger, "_connect"):
                with self.pg_logger._connect() as runtime_conn:
                    with runtime_conn.cursor() as cur:
                        cur.execute(sql, (symbol,))
                        row = cur.fetchone()
                        return str(row[0]) if row else None
            if conn is not None:
                with conn.cursor() as cur:
                    cur.execute(sql, (symbol,))
                    row = cur.fetchone()
                    return str(row[0]) if row else None
        except Exception:
            return None
        return None

    def _strategy_from_dynamic_watchlist(self, symbol: str) -> str | None:
        if self.pg_logger is None:
            return None

        sql = """
        select strategy
        from dynamic_watchlist
        where symbol = %s
          and source = 'opportunity_scanner'
          and is_active = true
          and strategy is not null
          and strategy <> ''
        order by priority desc, updated_at desc
        limit 1
        """

        conn = getattr(self.pg_logger, "conn", None)

        if conn is None and hasattr(self.pg_logger, "_connect"):
            with self.pg_logger._connect() as runtime_conn:
                with runtime_conn.cursor() as cur:
                    cur.execute(sql, (symbol,))
                    row = cur.fetchone()
                    return str(row[0]) if row else None

        if conn is not None:
            with conn.cursor() as cur:
                cur.execute(sql, (symbol,))
                row = cur.fetchone()
                return str(row[0]) if row else None

        return None
