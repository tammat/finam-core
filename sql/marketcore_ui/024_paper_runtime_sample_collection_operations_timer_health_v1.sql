BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.paper_runtime_sample_collection_operations_timer_health_v1 (
    id SMALLINT PRIMARY KEY,

    timer_unit TEXT NOT NULL DEFAULT 'finam-paper-sample-operations.timer',
    service_unit TEXT NOT NULL DEFAULT 'finam-paper-sample-operations.service',

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

    operations_rows INTEGER NOT NULL DEFAULT 0,
    operations_high_rows INTEGER NOT NULL DEFAULT 0,
    operations_near_ready_rows INTEGER NOT NULL DEFAULT 0,
    operations_collecting_rows INTEGER NOT NULL DEFAULT 0,
    operations_micro_live_allowed_rows INTEGER NOT NULL DEFAULT 0,

    operations_refreshed_at TIMESTAMPTZ,
    operations_age_sec INTEGER,
    operations_stale BOOLEAN NOT NULL DEFAULT true,

    phase_result_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    engineering_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    operational_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    phase_timer_health_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    next_phase TEXT NOT NULL DEFAULT '',

    health_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    health_reason TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',

    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,

    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_version TEXT NOT NULL DEFAULT 'PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_TIMER_HEALTH_V1',
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.paper_runtime_sample_collection_operations_timer_health_v1 TO alex;

COMMIT;

SELECT 'PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_TIMER_HEALTH_SCHEMA_V1_READY' AS verdict;
