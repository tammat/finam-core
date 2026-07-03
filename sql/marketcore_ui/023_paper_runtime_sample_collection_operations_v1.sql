BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.paper_runtime_sample_collection_operations_v1 (
    operation_rank INTEGER PRIMARY KEY,

    symbol TEXT NOT NULL DEFAULT '',
    strategy TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL DEFAULT '',
    side TEXT NOT NULL DEFAULT '',

    sample_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    readiness_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    backtest_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    oos_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    robustness_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    total_trades INTEGER NOT NULL DEFAULT 0,
    required_total_trades INTEGER NOT NULL DEFAULT 30,
    remaining_total_trades INTEGER NOT NULL DEFAULT 0,

    oos_trades INTEGER NOT NULL DEFAULT 0,
    required_oos_trades INTEGER NOT NULL DEFAULT 10,
    remaining_oos_trades INTEGER NOT NULL DEFAULT 0,

    progress_pct NUMERIC(10,2) NOT NULL DEFAULT 0,

    operation_priority TEXT NOT NULL DEFAULT 'NORMAL',
    operation_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    operation_reason TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',
    next_check TEXT NOT NULL DEFAULT '',

    timer_health_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    collection_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    phase_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    micro_live_ready BOOLEAN NOT NULL DEFAULT false,
    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,

    source_monitor_rank INTEGER,
    source_version TEXT NOT NULL DEFAULT 'PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.paper_runtime_sample_collection_operations_v1 TO alex;

COMMIT;

SELECT 'PAPER_RUNTIME_SAMPLE_COLLECTION_OPERATIONS_SCHEMA_V1_READY' AS verdict;
