from __future__ import annotations

import psycopg

from finam_core.analytics.symbol_strategy_mapper import map_symbol_to_strategy


class SymbolStrategyResolver:
    """
    Русский комментарий:
    Strategy resolver для analytics/advisory.

    Приоритет:
    1. runtime_active_universe
    2. dynamic_watchlist
    3. fallback mapper
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def resolve(self, symbol: str) -> str:
        value = str(symbol).strip()

        for table in ("runtime_active_universe", "dynamic_watchlist"):
            strategy = self._resolve_from_table(table=table, symbol=value)
            if strategy:
                return strategy

        return map_symbol_to_strategy(value)

    def _resolve_from_table(self, table: str, symbol: str) -> str | None:
        sql = f"""
        SELECT strategy
        FROM {table}
        WHERE symbol = %s
          AND strategy IS NOT NULL
          AND strategy <> ''
        ORDER BY
          CASE
            WHEN EXISTS (
              SELECT 1
              FROM information_schema.columns
              WHERE table_name = %s
                AND column_name = 'updated_at'
            )
            THEN 1 ELSE 0
          END DESC
        LIMIT 1
        """

        try:
            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (symbol, table))
                    row = cur.fetchone()
                    return str(row[0]) if row else None
        except Exception:
            return None
