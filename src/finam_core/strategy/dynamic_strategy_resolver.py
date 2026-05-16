from __future__ import annotations

from typing import Any

from finam_core.strategy.symbol_strategy_map import SYMBOL_STRATEGY_MAP, DEFAULT_STRATEGY


class DynamicStrategyResolver:
    """Русский комментарий: выбирает стратегию из dynamic_watchlist, иначе fallback на SYMBOL_STRATEGY_MAP."""

    def __init__(self, pg_logger: Any | None = None) -> None:
        self.pg_logger = pg_logger

    def strategy_for_symbol(self, symbol: str) -> str:
        dynamic = self._strategy_from_dynamic_watchlist(symbol)
        if dynamic:
            return dynamic

        return str(SYMBOL_STRATEGY_MAP.get(symbol, DEFAULT_STRATEGY))

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
