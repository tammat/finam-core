BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.paper_edge_market_universe_candidates_v1 (
    candidate_rank INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    asset_class TEXT NOT NULL DEFAULT 'UNKNOWN',

    bars_total INTEGER NOT NULL DEFAULT 0,
    latest_ts TIMESTAMPTZ,
    latest_close NUMERIC(20,8),
    latest_volume NUMERIC(20,4),
    data_age_sec INTEGER,

    universe_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    candidate_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    score NUMERIC(10,4) NOT NULL DEFAULT 0,

    recommended_action TEXT NOT NULL DEFAULT '',
    source_version TEXT NOT NULL DEFAULT 'PAPER_EDGE_DISCOVERY_MARKET_UNIVERSE_CANDIDATES_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_id TEXT NOT NULL DEFAULT 'manual',

    UNIQUE(symbol, timeframe)
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.paper_edge_market_universe_candidates_v1 TO alex;

COMMIT;

SELECT 'PAPER_EDGE_MARKET_UNIVERSE_CANDIDATES_SCHEMA_V1_READY' AS verdict;
