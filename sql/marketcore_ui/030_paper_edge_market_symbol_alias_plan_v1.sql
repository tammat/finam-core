BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.paper_edge_market_symbol_alias_plan_v1 (
    plan_rank INTEGER PRIMARY KEY,

    candidate_symbol TEXT NOT NULL DEFAULT '',
    candidate_root TEXT NOT NULL DEFAULT '',
    candidate_strategy TEXT NOT NULL DEFAULT '',
    candidate_timeframe TEXT NOT NULL DEFAULT '',
    side TEXT NOT NULL DEFAULT '',

    alias_symbol TEXT NOT NULL DEFAULT '',
    alias_timeframe TEXT NOT NULL DEFAULT '',
    alias_source_table TEXT NOT NULL DEFAULT '',

    alias_bars_total INTEGER NOT NULL DEFAULT 0,
    alias_latest_bar_ts TIMESTAMPTZ,
    alias_market_data_age_sec INTEGER,

    alias_match_type TEXT NOT NULL DEFAULT 'UNKNOWN',
    alias_confidence NUMERIC(10,4) NOT NULL DEFAULT 0,

    alias_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    diagnosis TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',

    source_freshness_rank INTEGER,
    source_version TEXT NOT NULL DEFAULT 'PAPER_EDGE_DISCOVERY_MARKET_SYMBOL_ALIAS_PLAN_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.paper_edge_market_symbol_alias_plan_v1 TO alex;

COMMIT;

SELECT 'PAPER_EDGE_MARKET_SYMBOL_ALIAS_PLAN_SCHEMA_V1_READY' AS verdict;
