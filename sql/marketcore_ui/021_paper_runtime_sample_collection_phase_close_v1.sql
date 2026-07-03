BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.paper_runtime_sample_collection_phase_close_v1 (
    id SMALLINT PRIMARY KEY,

    phase_name TEXT NOT NULL DEFAULT 'PAPER_RUNTIME_SAMPLE_COLLECTION',
    engineering_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    operational_status TEXT NOT NULL DEFAULT 'UNKNOWN',

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
    collection_phase_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    timer_health_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    timer_healthy BOOLEAN NOT NULL DEFAULT false,
    service_healthy BOOLEAN NOT NULL DEFAULT false,
    sample_summary_stale BOOLEAN NOT NULL DEFAULT true,
    sample_summary_age_sec INTEGER,

    micro_live_ready_rows INTEGER NOT NULL DEFAULT 0,
    micro_live_allowed_rows INTEGER NOT NULL DEFAULT 0,
    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,

    close_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    close_reason TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',
    next_phase TEXT NOT NULL DEFAULT '',

    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL DEFAULT 'PAPER_RUNTIME_SAMPLE_COLLECTION_PHASE_CLOSE_V1',
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.paper_runtime_sample_collection_phase_close_v1 TO alex;

COMMIT;

SELECT 'PAPER_RUNTIME_SAMPLE_COLLECTION_PHASE_CLOSE_SCHEMA_V1_READY' AS verdict;
