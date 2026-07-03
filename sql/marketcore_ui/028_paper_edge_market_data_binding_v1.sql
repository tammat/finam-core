BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.paper_edge_market_data_binding_v1 (
    binding_rank INTEGER PRIMARY KEY,

    symbol TEXT NOT NULL DEFAULT '',
    strategy TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL DEFAULT '',
    side TEXT NOT NULL DEFAULT '',

    market_symbol TEXT NOT NULL DEFAULT '',
    market_timeframe TEXT NOT NULL DEFAULT '',
    bars_source_table TEXT NOT NULL DEFAULT '',

    bars_total INTEGER NOT NULL DEFAULT 0,
    latest_bar_ts TIMESTAMPTZ,
    latest_close NUMERIC(20,8),
    latest_volume NUMERIC(20,4),
    market_data_age_sec INTEGER,

    market_data_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    binding_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    binding_reason TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',

    source_candidate_rank INTEGER,
    source_version TEXT NOT NULL DEFAULT 'PAPER_EDGE_DISCOVERY_MARKET_DATA_BINDING_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.paper_edge_market_data_binding_v1 TO alex;

COMMIT;

SELECT 'PAPER_EDGE_MARKET_DATA_BINDING_SCHEMA_V1_READY' AS verdict;
