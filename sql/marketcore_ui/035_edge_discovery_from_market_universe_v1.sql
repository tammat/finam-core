BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.edge_discovery_from_market_universe_v1 (
    discovery_rank INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    strategy_family TEXT NOT NULL,

    bars_total INTEGER NOT NULL DEFAULT 0,
    trades_count INTEGER NOT NULL DEFAULT 0,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,

    winrate NUMERIC(10,4) NOT NULL DEFAULT 0,
    gross_pnl NUMERIC(20,8) NOT NULL DEFAULT 0,
    avg_pnl NUMERIC(20,8) NOT NULL DEFAULT 0,
    profit_factor NUMERIC(20,8),
    expectancy NUMERIC(20,8) NOT NULL DEFAULT 0,

    edge_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    discovery_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    recommended_action TEXT NOT NULL DEFAULT '',

    source_queue_rank INTEGER,
    source_version TEXT NOT NULL DEFAULT 'EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.edge_discovery_from_market_universe_v1 TO alex;

COMMIT;

SELECT 'EDGE_DISCOVERY_FROM_MARKET_UNIVERSE_SCHEMA_V1_READY' AS verdict;
