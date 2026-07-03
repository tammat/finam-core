BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.paper_runtime_sample_collection_operations_daily_summary_v1 (
    id SMALLINT PRIMARY KEY,
    summary_date DATE NOT NULL DEFAULT CURRENT_DATE,

    phase_result_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    engineering_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    operational_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    phase_close_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    sample_collection_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    sample_phase_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    timer_health_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    operations_health_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    operations_rows INTEGER NOT NULL DEFAULT 0,
    operations_high_rows INTEGER NOT NULL DEFAULT 0,
    operations_near_ready_rows INTEGER NOT NULL DEFAULT 0,
    operations_collecting_rows INTEGER NOT NULL DEFAULT 0,

    candidates_total INTEGER NOT NULL DEFAULT 0,
    sample_ready INTEGER NOT NULL DEFAULT 0,
    wait_both_sample INTEGER NOT NULL DEFAULT 0,

    avg_progress_pct NUMERIC(10,2) NOT NULL DEFAULT 0,
    max_progress_pct NUMERIC(10,2) NOT NULL DEFAULT 0,
    min_remaining_total_trades INTEGER,
    min_remaining_oos_trades INTEGER,

    micro_live_allowed_rows INTEGER NOT NULL DEFAULT 0,
    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,

    daily_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    conclusion TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',

    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL DEFAULT 'PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_DAILY_SUMMARY_V1',
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.paper_runtime_sample_collection_operations_daily_summary_v1 TO alex;

COMMIT;

SELECT 'PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_DAILY_SUMMARY_SCHEMA_V1_READY' AS verdict;
