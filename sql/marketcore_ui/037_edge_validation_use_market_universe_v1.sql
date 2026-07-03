BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.edge_validation_use_market_universe_v1 (
    validation_rank INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL DEFAULT '',
    asset_class TEXT NOT NULL DEFAULT '',
    strategy TEXT NOT NULL DEFAULT '',
    side TEXT NOT NULL DEFAULT '',

    source_queue_rank INTEGER,
    total_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    research_priority TEXT NOT NULL DEFAULT '',
    ranking_status TEXT NOT NULL DEFAULT '',

    validation_source TEXT NOT NULL DEFAULT 'marketcore_ui.market_universe_research_queue_v1',
    legacy_source TEXT NOT NULL DEFAULT 'marketcore_ui.paper_edge_research_candidates_v1',

    validation_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    validation_stage TEXT NOT NULL DEFAULT 'QUEUE',
    recommended_action TEXT NOT NULL DEFAULT '',

    runtime_changed INTEGER NOT NULL DEFAULT 0,
    execution_changed INTEGER NOT NULL DEFAULT 0,
    orders_changed INTEGER NOT NULL DEFAULT 0,
    fills_changed INTEGER NOT NULL DEFAULT 0,
    micro_live_allowed INTEGER NOT NULL DEFAULT 0,

    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL DEFAULT 'EDGE_VALIDATION_USE_MARKET_UNIVERSE_V1',
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.edge_validation_use_market_universe_v1 TO alex;

COMMIT;

SELECT 'EDGE_VALIDATION_USE_MARKET_UNIVERSE_SCHEMA_V1_READY' AS verdict;
