BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.micro_live_readiness_v1 (
    readiness_rank INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL DEFAULT '',
    strategy TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL DEFAULT '',
    side TEXT NOT NULL DEFAULT '',

    backtest_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    oos_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    robustness_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    readiness_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    micro_live_ready BOOLEAN NOT NULL DEFAULT false,
    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,

    total_trades INTEGER NOT NULL DEFAULT 0,
    in_sample_trades INTEGER NOT NULL DEFAULT 0,
    oos_trades INTEGER NOT NULL DEFAULT 0,

    in_sample_pnl NUMERIC(20,6),
    oos_pnl NUMERIC(20,6),
    in_sample_expectancy NUMERIC(20,6),
    oos_expectancy NUMERIC(20,6),
    in_sample_profit_factor NUMERIC(20,6),
    oos_profit_factor NUMERIC(20,6),
    in_sample_winrate NUMERIC(20,6),
    oos_winrate NUMERIC(20,6),
    stability_score NUMERIC(20,6) NOT NULL DEFAULT 0,

    block_reason TEXT NOT NULL DEFAULT '',
    evidence_summary TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',

    source_backtest_rank INTEGER,
    source_version TEXT NOT NULL DEFAULT 'MICRO_LIVE_READINESS_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    build_id TEXT NOT NULL DEFAULT 'manual'
);

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.micro_live_readiness_v1 TO alex;

COMMIT;

SELECT 'MICRO_LIVE_READINESS_SCHEMA_V1_READY' AS verdict;
