BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.phase_ii_paper_edge_discovery_summary_v1 (
    id SMALLINT PRIMARY KEY,

    phase_name TEXT NOT NULL DEFAULT 'PHASE_II_PAPER_EDGE_DISCOVERY',
    phase_result_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    engineering_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    operational_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    close_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    timer_health_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    collection_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    collection_phase_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    candidates_total INTEGER NOT NULL DEFAULT 0,
    sample_ready INTEGER NOT NULL DEFAULT 0,
    wait_both_sample INTEGER NOT NULL DEFAULT 0,
    wait_total_sample INTEGER NOT NULL DEFAULT 0,
    wait_oos_sample INTEGER NOT NULL DEFAULT 0,

    min_remaining_total_trades INTEGER,
    min_remaining_oos_trades INTEGER,
    avg_progress_pct NUMERIC(10,2) NOT NULL DEFAULT 0,
    max_progress_pct NUMERIC(10,2) NOT NULL DEFAULT 0,

    paper_candidates_rows INTEGER NOT NULL DEFAULT 0,
    validation_queue_rows INTEGER NOT NULL DEFAULT 0,
    validation_pipeline_rows INTEGER NOT NULL DEFAULT 0,
    robustness_rows INTEGER NOT NULL DEFAULT 0,
    oos_validation_rows INTEGER NOT NULL DEFAULT 0,
    oos_backtest_rows INTEGER NOT NULL DEFAULT 0,
    micro_live_readiness_rows INTEGER NOT NULL DEFAULT 0,
    sample_monitor_rows INTEGER NOT NULL DEFAULT 0,

    micro_live_ready_rows INTEGER NOT NULL DEFAULT 0,
    micro_live_allowed_rows INTEGER NOT NULL DEFAULT 0,
    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,

    conclusion TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',
    next_phase TEXT NOT NULL DEFAULT '',

    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL DEFAULT 'PHASE_II_PAPER_EDGE_DISCOVERY_SUMMARY_V1',
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.phase_ii_paper_edge_discovery_summary_v1 TO alex;

COMMIT;

SELECT 'PHASE_II_PAPER_EDGE_DISCOVERY_SUMMARY_SCHEMA_V1_READY' AS verdict;
