BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.paper_sample_accumulation_monitor_v1 (
    monitor_rank INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL DEFAULT '',
    strategy TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL DEFAULT '',
    side TEXT NOT NULL DEFAULT '',

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

    sample_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    progress_pct NUMERIC(10,2) NOT NULL DEFAULT 0,

    micro_live_ready BOOLEAN NOT NULL DEFAULT false,
    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,

    block_reason TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',

    source_readiness_rank INTEGER,
    source_version TEXT NOT NULL DEFAULT 'PAPER_SAMPLE_ACCUMULATION_MONITOR_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.paper_sample_accumulation_monitor_v1 TO alex;

COMMIT;

SELECT 'PAPER_SAMPLE_ACCUMULATION_MONITOR_SCHEMA_V1_READY' AS verdict;
