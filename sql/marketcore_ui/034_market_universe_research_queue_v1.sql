BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.market_universe_research_queue_v1 (
    queue_rank INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    total_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    ranking_status TEXT NOT NULL DEFAULT '',
    research_priority TEXT NOT NULL DEFAULT 'NORMAL',
    research_status TEXT NOT NULL DEFAULT 'QUEUED',
    recommended_strategy_family TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',
    source_rank INTEGER,
    source_version TEXT NOT NULL DEFAULT 'MARKET_UNIVERSE_RESEARCH_QUEUE_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_id TEXT NOT NULL DEFAULT 'manual',
    UNIQUE(symbol, timeframe)
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.market_universe_research_queue_v1 TO alex;

COMMIT;

SELECT 'MARKET_UNIVERSE_RESEARCH_QUEUE_SCHEMA_V1_READY' AS verdict;
