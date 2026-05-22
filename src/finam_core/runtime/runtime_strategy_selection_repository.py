from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


@dataclass(frozen=True)
class RuntimeStrategySelectionRecord:
    symbol: str
    strategy: str
    timeframe: str
    mode: str
    enabled: bool
    reason: str
    updated_at: datetime


class RuntimeStrategySelectionRepository:
    """
    Русский комментарий:
    Хранит runtime-решение:
    какие стратегии допускаются в runtime.
    """

    def __init__(self, dsn: str | None = None):
        self.dsn = dsn or build_psycopg_url()

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS runtime_strategy_selection (
            id BIGSERIAL PRIMARY KEY,

            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL,
            timeframe TEXT NOT NULL,

            mode TEXT NOT NULL,
            enabled BOOLEAN NOT NULL,

            reason TEXT NOT NULL,

            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            UNIQUE(symbol, strategy, timeframe)
        );

        CREATE INDEX IF NOT EXISTS idx_runtime_strategy_selection_symbol
        ON runtime_strategy_selection(symbol);

        CREATE INDEX IF NOT EXISTS idx_runtime_strategy_selection_mode
        ON runtime_strategy_selection(mode);

        CREATE INDEX IF NOT EXISTS idx_runtime_strategy_selection_enabled
        ON runtime_strategy_selection(enabled);
        """

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def save(
        self,
        record: RuntimeStrategySelectionRecord,
    ) -> None:
        sql = """
        INSERT INTO runtime_strategy_selection (
            symbol,
            strategy,
            timeframe,
            mode,
            enabled,
            reason,
            updated_at
        )
        VALUES (
            %s,%s,%s,%s,%s,%s,%s
        )
        ON CONFLICT(symbol, strategy, timeframe)
        DO UPDATE SET
            mode = EXCLUDED.mode,
            enabled = EXCLUDED.enabled,
            reason = EXCLUDED.reason,
            updated_at = EXCLUDED.updated_at
        """

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        record.symbol,
                        record.strategy,
                        record.timeframe,
                        record.mode,
                        record.enabled,
                        record.reason,
                        record.updated_at,
                    ),
                )
            conn.commit()

    def load_enabled(self) -> list[RuntimeStrategySelectionRecord]:
        sql = """
        SELECT
            symbol,
            strategy,
            timeframe,
            mode,
            enabled,
            reason,
            updated_at
        FROM runtime_strategy_selection
        WHERE enabled = TRUE
        ORDER BY updated_at DESC
        """

        items = []

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)

                for row in cur.fetchall():
                    items.append(
                        RuntimeStrategySelectionRecord(
                            symbol=str(row[0]),
                            strategy=str(row[1]),
                            timeframe=str(row[2]),
                            mode=str(row[3]),
                            enabled=bool(row[4]),
                            reason=str(row[5]),
                            updated_at=row[6],
                        )
                    )

        return items

    @staticmethod
    def now_utc() -> datetime:
        return datetime.now(timezone.utc)
