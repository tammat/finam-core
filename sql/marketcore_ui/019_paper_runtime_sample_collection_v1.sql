BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.paper_runtime_sample_collection_v1 (
    id SMALLINT PRIMARY KEY,
    candidates_total INTEGER NOT NULL DEFAULT 0,
    sample_ready INTEGER NOT NULL DEFAULT 0,
    wait_both_sample INTEGER NOT NULL DEFAULT 0,
    wait_total_sample INTEGER NOT NULL DEFAULT 0,
    wait_oos_sample INTEGER NOT NULL DEFAULT 0,
    min_remaining_total_trades INTEGER,
    min_remaining_oos_trades INTEGER,
    avg_progress_pct NUMERIC(10,2) NOT NULL DEFAULT 0,
    max_progress_pct NUMERIC(10,2) NOT NULL DEFAULT 0,
    collection_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    phase_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    recommended_action TEXT NOT NULL DEFAULT '',
    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL DEFAULT 'PAPER_RUNTIME_SAMPLE_COLLECTION_V1',
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.paper_runtime_sample_collection_v1 TO alex;

COMMIT;

SELECT 'PAPER_RUNTIME_SAMPLE_COLLECTION_SCHEMA_V1_READY' AS verdict;
