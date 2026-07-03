BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.paper_runtime_sample_collection_timer_health_v1 (
    id SMALLINT PRIMARY KEY,

    timer_unit TEXT NOT NULL DEFAULT 'finam-paper-sample-collection.timer',
    service_unit TEXT NOT NULL DEFAULT 'finam-paper-sample-collection.service',

    timer_active_state TEXT NOT NULL DEFAULT 'unknown',
    timer_sub_state TEXT NOT NULL DEFAULT 'unknown',
    timer_unit_file_state TEXT NOT NULL DEFAULT 'unknown',
    timer_next_elapse TEXT NOT NULL DEFAULT '',
    timer_last_trigger TEXT NOT NULL DEFAULT '',
    timer_healthy BOOLEAN NOT NULL DEFAULT false,

    service_active_state TEXT NOT NULL DEFAULT 'unknown',
    service_sub_state TEXT NOT NULL DEFAULT 'unknown',
    service_result TEXT NOT NULL DEFAULT 'unknown',
    service_exec_main_status TEXT NOT NULL DEFAULT '',
    service_last_exit TEXT NOT NULL DEFAULT '',
    service_healthy BOOLEAN NOT NULL DEFAULT false,

    sample_summary_exists BOOLEAN NOT NULL DEFAULT false,
    sample_summary_refreshed_at TIMESTAMPTZ,
    sample_summary_age_sec INTEGER,
    sample_summary_stale BOOLEAN NOT NULL DEFAULT true,

    candidates_total INTEGER NOT NULL DEFAULT 0,
    sample_ready INTEGER NOT NULL DEFAULT 0,
    collection_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    phase_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,

    timer_health_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    health_reason TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',

    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL DEFAULT 'PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_V1',
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.paper_runtime_sample_collection_timer_health_v1 TO alex;

COMMIT;

SELECT 'PAPER_RUNTIME_SAMPLE_COLLECTION_TIMER_HEALTH_SCHEMA_V1_READY' AS verdict;
