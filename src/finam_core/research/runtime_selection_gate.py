from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg


@dataclass(frozen=True)
class RuntimeSelectionDecision:
    """Решение runtime-gate по связке strategy + root_symbol + regime."""

    allowed: bool
    reason: str
    strategy: str
    symbol: str
    root_symbol: str
    regime: str


def normalize_root_symbol(symbol: str) -> str:
    """Русский комментарий: нормализуем конкретный контракт до базового инструмента."""
    if symbol.startswith("NG") and symbol.endswith("@RTSX"):
        return "NG"
    if symbol.startswith("BR") and symbol.endswith("@RTSX"):
        return "BR"
    if symbol.startswith("USDRUB") and symbol.endswith("@RTSX"):
        return "USDRUB"
    return symbol


class RuntimeSelectionGate:
    """Русский комментарий: read-only gate допуска стратегии в runtime."""

    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.environ["DATABASE_URL"]

    def is_allowed(self, *, strategy: str, symbol: str, regime: str) -> RuntimeSelectionDecision:
        root_symbol = normalize_root_symbol(symbol)

        sql = """
        SELECT reason
        FROM strategy_selection_runtime_normalized
        WHERE strategy = %(strategy)s
          AND root_symbol = %(root_symbol)s
          AND regime = %(regime)s
          AND status = 'PROMOTED_RUNTIME'
        LIMIT 1;
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    {
                        "strategy": strategy,
                        "root_symbol": root_symbol,
                        "regime": regime,
                    },
                )
                row = cur.fetchone()

        if row:
            return RuntimeSelectionDecision(
                allowed=True,
                reason="Связка разрешена selection layer",
                strategy=strategy,
                symbol=symbol,
                root_symbol=root_symbol,
                regime=regime,
            )

        return RuntimeSelectionDecision(
            allowed=False,
            reason="Связка не разрешена selection layer",
            strategy=strategy,
            symbol=symbol,
            root_symbol=root_symbol,
            regime=regime,
        )
