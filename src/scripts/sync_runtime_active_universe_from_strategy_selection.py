from __future__ import annotations

from finam_core.analytics.statistics_repository import build_psycopg_url
import psycopg


def main() -> int:
    sql_migrate = """
    CREATE TABLE IF NOT EXISTS runtime_active_universe (
        id BIGSERIAL PRIMARY KEY,
        symbol TEXT NOT NULL,
        strategy TEXT NOT NULL,
        timeframe TEXT NOT NULL DEFAULT 'M5',
        is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
        priority INTEGER NOT NULL DEFAULT 0,
        source TEXT NOT NULL DEFAULT 'strategy_selection',
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE(symbol, strategy, timeframe)
    );

    ALTER TABLE runtime_active_universe
    ADD COLUMN IF NOT EXISTS timeframe TEXT NOT NULL DEFAULT 'M5',
    ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'strategy_selection',
    ADD COLUMN IF NOT EXISTS priority INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();

    CREATE INDEX IF NOT EXISTS idx_runtime_active_universe_enabled
    ON runtime_active_universe(is_enabled, priority DESC);

    CREATE INDEX IF NOT EXISTS idx_runtime_active_universe_symbol
    ON runtime_active_universe(symbol);
    """

    sql_sync = """
    INSERT INTO runtime_active_universe (
        symbol,
        strategy,
        timeframe,
        is_enabled,
        priority,
        source,
        updated_at
    )
    SELECT DISTINCT ON (symbol)
        symbol,
        strategy,
        timeframe,
        enabled,
        CASE
            WHEN mode = 'PAPER_ENABLED' THEN 100
            WHEN mode = 'RADAR_ONLY' THEN 50
            WHEN mode = 'RESEARCH_ONLY' THEN 10
            ELSE 0
        END AS priority,
        'strategy_selection',
        now()
    FROM runtime_strategy_selection
    WHERE mode IN ('PAPER_ENABLED', 'RADAR_ONLY', 'RESEARCH_ONLY')
    ORDER BY
        symbol,
        CASE
            WHEN mode = 'PAPER_ENABLED' THEN 100
            WHEN mode = 'RADAR_ONLY' THEN 50
            WHEN mode = 'RESEARCH_ONLY' THEN 10
            ELSE 0
        END DESC,
        updated_at DESC
    ON CONFLICT (symbol)
    DO UPDATE SET
        strategy = EXCLUDED.strategy,
        timeframe = EXCLUDED.timeframe,
        is_enabled = EXCLUDED.is_enabled,
        priority = EXCLUDED.priority,
        source = EXCLUDED.source,
        updated_at = now()
    """
    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_migrate)
            cur.execute(sql_sync)
            inserted = cur.rowcount
        conn.commit()

    print(
        "SYNC_RUNTIME_ACTIVE_UNIVERSE_FROM_STRATEGY_SELECTION_OK "
        f"rows={inserted}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
