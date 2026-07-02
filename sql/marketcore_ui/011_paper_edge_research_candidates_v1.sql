BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.paper_edge_research_candidates_v1 (
    candidate_rank INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL DEFAULT '',
    strategy TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL DEFAULT '',
    side TEXT NOT NULL DEFAULT '',
    candidate_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    expectancy NUMERIC(20,6),
    profit_factor NUMERIC(20,6),
    winrate NUMERIC(20,6),
    trades INTEGER,
    net_pnl NUMERIC(20,6),
    score NUMERIC(20,6),
    source_table TEXT NOT NULL DEFAULT '',
    source_version TEXT NOT NULL DEFAULT 'PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.paper_edge_research_candidates_v1 TO alex;

COMMIT;

SELECT 'PAPER_EDGE_DISCOVERY_RESEARCH_CANDIDATES_SCHEMA_V1_READY' AS verdict;
