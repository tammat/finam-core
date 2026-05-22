from __future__ import annotations

import psycopg

from finam_core.runtime.strategy_lifecycle_state_machine import StrategyLifecycleDecision


class StrategyLifecycleRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS strategy_lifecycle_state (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            lifecycle_state TEXT NOT NULL,
            allow_runtime BOOLEAN NOT NULL,
            allow_radar BOOLEAN NOT NULL,
            allow_research BOOLEAN NOT NULL,
            reason TEXT NOT NULL DEFAULT '',
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(symbol, strategy, timeframe)
        );

        CREATE INDEX IF NOT EXISTS idx_strategy_lifecycle_state_state
        ON strategy_lifecycle_state(lifecycle_state);

        CREATE INDEX IF NOT EXISTS idx_strategy_lifecycle_state_symbol
        ON strategy_lifecycle_state(symbol);
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def save(self, items: list[StrategyLifecycleDecision]) -> int:
        sql = """
        INSERT INTO strategy_lifecycle_state (
            symbol,
            strategy,
            timeframe,
            lifecycle_state,
            allow_runtime,
            allow_radar,
            allow_research,
            reason,
            updated_at
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,now())
        ON CONFLICT (symbol, strategy, timeframe)
        DO UPDATE SET
            lifecycle_state = EXCLUDED.lifecycle_state,
            allow_runtime = EXCLUDED.allow_runtime,
            allow_radar = EXCLUDED.allow_radar,
            allow_research = EXCLUDED.allow_research,
            reason = EXCLUDED.reason,
            updated_at = now()
        """

        saved = 0

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                for item in items:
                    cur.execute(
                        sql,
                        (
                            item.symbol,
                            item.strategy,
                            item.timeframe,
                            item.lifecycle_state,
                            item.allow_runtime,
                            item.allow_radar,
                            item.allow_research,
                            item.reason,
                        ),
                    )
                    saved += cur.rowcount
            conn.commit()

        return saved
