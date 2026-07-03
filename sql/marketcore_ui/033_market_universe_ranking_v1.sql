BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.market_universe_ranking_v1 (
    rank INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    bars_total INTEGER NOT NULL DEFAULT 0,
    latest_ts TIMESTAMPTZ,
    latest_close NUMERIC(20,8),
    latest_volume NUMERIC(20,4),
    data_age_sec INTEGER,

    freshness_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    history_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    liquidity_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    timeframe_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    asset_priority_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    total_score NUMERIC(10,4) NOT NULL DEFAULT 0,

    ranking_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    recommended_action TEXT NOT NULL DEFAULT '',

    source_version TEXT NOT NULL DEFAULT 'MARKET_UNIVERSE_RANKING_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_id TEXT NOT NULL DEFAULT 'manual',

    UNIQUE(symbol, timeframe)
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.market_universe_ranking_v1 TO alex;

COMMIT;

SELECT 'MARKET_UNIVERSE_RANKING_SCHEMA_V1_READY' AS verdict;
