CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.profit_factory_candidate_v1 (
    candidate_id TEXT PRIMARY KEY,
    workflow_run_id BIGINT,

    symbol TEXT NOT NULL,
    strategy_code TEXT NOT NULL,
    timeframe TEXT NOT NULL,

    factory_stage TEXT NOT NULL DEFAULT 'RESEARCH',
    stage_status TEXT NOT NULL DEFAULT 'PENDING',
    stage_entered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    stage_exited_at TIMESTAMPTZ,
    reason_code TEXT NOT NULL DEFAULT 'AWAITING_EVALUATION',

    expected_profit NUMERIC(20,6) NOT NULL DEFAULT 0,
    realized_profit NUMERIC(20,6) NOT NULL DEFAULT 0,
    capital_allocated NUMERIC(20,6) NOT NULL DEFAULT 0,
    factory_roi NUMERIC(20,8) GENERATED ALWAYS AS (
        CASE
            WHEN capital_allocated = 0 THEN 0
            ELSE realized_profit / capital_allocated
        END
    ) STORED,
    max_drawdown NUMERIC(20,6) NOT NULL DEFAULT 0,
    confidence_score NUMERIC(10,6) NOT NULL DEFAULT 0,

    operator_decision TEXT NOT NULL DEFAULT 'HOLD',
    decision_reason_code TEXT NOT NULL DEFAULT 'INSUFFICIENT_EVIDENCE',
    decision_expected_impact NUMERIC(20,6) NOT NULL DEFAULT 0,

    source_table TEXT NOT NULL DEFAULT '',
    source_id TEXT NOT NULL DEFAULT '',
    source_version TEXT NOT NULL DEFAULT 'PROFIT_FACTORY_CONTRACT_V1',
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT ck_profit_factory_stage_v1 CHECK (
        factory_stage IN (
            'RESEARCH', 'VALIDATION', 'EDGE', 'PAPER',
            'RUNTIME', 'PRODUCTION', 'STOPPED'
        )
    ),
    CONSTRAINT ck_profit_factory_stage_status_v1 CHECK (
        stage_status IN ('PENDING', 'ACTIVE', 'PASSED', 'BLOCKED', 'FAILED', 'STOPPED')
    ),
    CONSTRAINT ck_profit_factory_operator_decision_v1 CHECK (
        operator_decision IN ('PROMOTE', 'CONTINUE', 'HOLD', 'INVESTIGATE', 'REDUCE', 'STOP')
    ),
    CONSTRAINT ck_profit_factory_stage_time_v1 CHECK (
        stage_exited_at IS NULL OR stage_exited_at >= stage_entered_at
    ),
    CONSTRAINT ck_profit_factory_capital_v1 CHECK (capital_allocated >= 0),
    CONSTRAINT ck_profit_factory_drawdown_v1 CHECK (max_drawdown >= 0),
    CONSTRAINT ck_profit_factory_confidence_v1 CHECK (
        confidence_score >= 0 AND confidence_score <= 1
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_profit_factory_workflow_run_v1
ON analytics.profit_factory_candidate_v1(workflow_run_id)
WHERE workflow_run_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_profit_factory_stage_status_v1
ON analytics.profit_factory_candidate_v1(factory_stage, stage_status);

CREATE INDEX IF NOT EXISTS ix_profit_factory_operator_decision_v1
ON analytics.profit_factory_candidate_v1(operator_decision);

CREATE INDEX IF NOT EXISTS ix_profit_factory_expected_profit_v1
ON analytics.profit_factory_candidate_v1(expected_profit DESC);

CREATE OR REPLACE VIEW analytics.profit_factory_decision_queue_v1 AS
SELECT
    candidate_id,
    workflow_run_id,
    symbol,
    strategy_code,
    timeframe,
    factory_stage,
    stage_status,
    expected_profit,
    realized_profit,
    capital_allocated,
    factory_roi,
    max_drawdown,
    confidence_score,
    operator_decision,
    decision_reason_code,
    decision_expected_impact,
    reason_code,
    refreshed_at
FROM analytics.profit_factory_candidate_v1
ORDER BY decision_expected_impact DESC, expected_profit DESC, candidate_id;

COMMENT ON TABLE analytics.profit_factory_candidate_v1 IS
'Canonical candidate lifecycle contract for MarketCore Profit Factory V1.';

COMMENT ON COLUMN analytics.profit_factory_candidate_v1.candidate_id IS
'Stable identifier joining Research, Edge, Paper, Runtime, and Production.';

GRANT USAGE ON SCHEMA analytics TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.profit_factory_candidate_v1 TO alex;
GRANT SELECT ON analytics.profit_factory_decision_queue_v1 TO alex;
