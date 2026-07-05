CREATE TABLE IF NOT EXISTS analytics.strategy_library_v1 (
    strategy_code TEXT PRIMARY KEY,
    strategy_family TEXT NOT NULL,
    category TEXT NOT NULL,
    status_code TEXT NOT NULL DEFAULT 'EXPERIMENT',
    priority INTEGER NOT NULL DEFAULT 100,
    description TEXT NOT NULL DEFAULT '',
    default_timeframes TEXT[] NOT NULL DEFAULT ARRAY['M5'],
    default_symbols TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    parameter_schema JSONB NOT NULL DEFAULT '{}'::jsonb,
    enabled BOOLEAN NOT NULL DEFAULT true,
    source_version TEXT NOT NULL DEFAULT 'STRATEGY_LIBRARY_V1',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_strategy_library_v1_category
ON analytics.strategy_library_v1(category);

CREATE INDEX IF NOT EXISTS ix_strategy_library_v1_status
ON analytics.strategy_library_v1(status_code);

GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.strategy_library_v1 TO alex;
