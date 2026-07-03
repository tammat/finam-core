BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.edge_oos_validation_v1 (
    oos_rank INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL DEFAULT '',
    strategy TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL DEFAULT '',
    side TEXT NOT NULL DEFAULT '',

    robustness_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    oos_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    oos_readiness TEXT NOT NULL DEFAULT 'UNKNOWN',

    sample_size_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    pf_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    expectancy_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    winrate_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    pnl_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    robustness_score NUMERIC(20,6) NOT NULL DEFAULT 0,
    oos_required BOOLEAN NOT NULL DEFAULT false,
    micro_live_ready BOOLEAN NOT NULL DEFAULT false,

    expectancy NUMERIC(20,6),
    profit_factor NUMERIC(20,6),
    winrate NUMERIC(20,6),
    trades INTEGER,
    net_pnl NUMERIC(20,6),
    score NUMERIC(20,6),

    evidence_summary TEXT NOT NULL DEFAULT '',
    oos_reason TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',

    source_robustness_rank INTEGER,
    source_version TEXT NOT NULL DEFAULT 'EDGE_OOS_VALIDATION_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.edge_oos_validation_v1 TO alex;

COMMIT;

SELECT 'EDGE_OOS_VALIDATION_SCHEMA_V1_READY' AS verdict;
