BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.edge_validation_pipeline_v1 (
    pipeline_rank INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL DEFAULT '',
    strategy TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL DEFAULT '',
    side TEXT NOT NULL DEFAULT '',
    queue_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    priority TEXT NOT NULL DEFAULT 'NORMAL',

    sample_check_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    pf_check_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    expectancy_check_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    robustness_status TEXT NOT NULL DEFAULT 'PENDING',
    oos_status TEXT NOT NULL DEFAULT 'PENDING',

    pipeline_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    recommended_action TEXT NOT NULL DEFAULT '',

    expectancy NUMERIC(20,6),
    profit_factor NUMERIC(20,6),
    winrate NUMERIC(20,6),
    trades INTEGER,
    net_pnl NUMERIC(20,6),
    score NUMERIC(20,6),

    evidence_summary TEXT NOT NULL DEFAULT '',
    risk_notes TEXT NOT NULL DEFAULT '',

    source_queue_rank INTEGER,
    source_version TEXT NOT NULL DEFAULT 'EDGE_VALIDATION_PIPELINE_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.edge_validation_pipeline_v1 TO alex;

COMMIT;

SELECT 'EDGE_VALIDATION_PIPELINE_SCHEMA_V1_READY' AS verdict;
