from __future__ import annotations

import psycopg

from finam_core.portfolio.lifecycle_stale_position_advisor import (
    LifecycleStalePositionAdvice,
)


class LifecycleStalePositionRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS lifecycle_stale_position_advice_events (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            display_name TEXT NOT NULL DEFAULT '',
            action TEXT NOT NULL,
            severity TEXT NOT NULL,
            block_new_entries BOOLEAN NOT NULL,
            reason TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_lifecycle_stale_position_advice_created_at
        ON lifecycle_stale_position_advice_events(created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_lifecycle_stale_position_advice_symbol
        ON lifecycle_stale_position_advice_events(symbol, created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_lifecycle_stale_position_advice_action
        ON lifecycle_stale_position_advice_events(action, severity);
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def save_many(self, advices: list[LifecycleStalePositionAdvice]) -> None:
        sql = """
        INSERT INTO lifecycle_stale_position_advice_events (
            symbol,
            display_name,
            action,
            severity,
            block_new_entries,
            reason
        )
        VALUES (%s,%s,%s,%s,%s,%s)
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                for item in advices:
                    cur.execute(
                        sql,
                        (
                            item.symbol,
                            item.display_name,
                            item.action,
                            item.severity,
                            item.block_new_entries,
                            item.reason,
                        ),
                    )
            conn.commit()
