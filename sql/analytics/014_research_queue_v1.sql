CREATE TABLE IF NOT EXISTS analytics.research_queue_v1 (
    id BIGSERIAL PRIMARY KEY,

    research_code TEXT NOT NULL,
    strategy_code TEXT NOT NULL REFERENCES analytics.strategy_library_v1(strategy_code),

    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,

    parameter_set JSONB NOT NULL DEFAULT '{}'::jsonb,

    priority INTEGER NOT NULL DEFAULT 100,
    status_code TEXT NOT NULL DEFAULT 'QUEUED',

    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT NOT NULL DEFAULT '',

    source_version TEXT NOT NULL DEFAULT 'RESEARCH_QUEUE_V1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(strategy_code, symbol, timeframe, parameter_set)
);

CREATE INDEX IF NOT EXISTS ix_research_queue_v1_status
ON analytics.research_queue_v1(status_code);

CREATE INDEX IF NOT EXISTS ix_research_queue_v1_priority
ON analytics.research_queue_v1(priority);

CREATE INDEX IF NOT EXISTS ix_research_queue_v1_symbol
ON analytics.research_queue_v1(symbol);

GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.research_queue_v1 TO alex;
GRANT USAGE, SELECT ON SEQUENCE analytics.research_queue_v1_id_seq TO alex;
