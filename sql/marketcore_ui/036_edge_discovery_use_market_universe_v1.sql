BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.edge_discovery_use_market_universe_v1 (
    id SMALLINT PRIMARY KEY,
    legacy_source TEXT NOT NULL DEFAULT 'marketcore_ui.paper_edge_research_candidates_v1',
    new_source TEXT NOT NULL DEFAULT 'marketcore_ui.market_universe_research_queue_v1',
    legacy_rows INTEGER NOT NULL DEFAULT 0,
    legacy_symbols INTEGER NOT NULL DEFAULT 0,
    queue_rows INTEGER NOT NULL DEFAULT 0,
    queue_symbols INTEGER NOT NULL DEFAULT 0,
    ranking_rows INTEGER NOT NULL DEFAULT 0,
    universe_rows INTEGER NOT NULL DEFAULT 0,
    migration_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    diagnosis TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',
    runtime_changed INTEGER NOT NULL DEFAULT 0,
    execution_changed INTEGER NOT NULL DEFAULT 0,
    orders_changed INTEGER NOT NULL DEFAULT 0,
    fills_changed INTEGER NOT NULL DEFAULT 0,
    micro_live_allowed INTEGER NOT NULL DEFAULT 0,
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL DEFAULT 'EDGE_DISCOVERY_USE_MARKET_UNIVERSE_V1',
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.edge_discovery_use_market_universe_v1 TO alex;

COMMIT;

SELECT 'EDGE_DISCOVERY_USE_MARKET_UNIVERSE_SCHEMA_V1_READY' AS verdict;
