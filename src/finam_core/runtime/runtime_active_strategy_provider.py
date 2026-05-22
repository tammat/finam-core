from __future__ import annotations

from dataclasses import dataclass

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


@dataclass(frozen=True)
class RuntimeActiveStrategy:
    symbol: str
    strategy: str
    timeframe: str


class RuntimeActiveStrategyProvider:
    """
    Русский комментарий:
    Источник истины для RuntimeExecutionEngine:
    symbol + strategy + timeframe берутся из runtime_active_universe.
    """

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or build_psycopg_url()

    def resolve(self, symbol: str) -> RuntimeActiveStrategy:
        sql = """
        SELECT
            symbol,
            strategy,
            COALESCE(timeframe, 'M5') AS timeframe
        FROM runtime_active_universe
        WHERE symbol = %s
          AND is_enabled = TRUE
        ORDER BY priority DESC, updated_at DESC NULLS LAST
        LIMIT 1
        """

        try:
            with psycopg.connect(self.dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (symbol,))
                    row = cur.fetchone()
        except Exception:
            return RuntimeActiveStrategy(symbol=symbol, strategy="", timeframe="")

        if not row:
            return RuntimeActiveStrategy(symbol=symbol, strategy="", timeframe="")

        return RuntimeActiveStrategy(
            symbol=str(row[0]),
            strategy=str(row[1] or ""),
            timeframe=str(row[2] or "M5"),
        )
