CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS analytics.edge_lab_run_v1 (
    id BIGSERIAL PRIMARY KEY,
    run_uuid UUID NOT NULL DEFAULT gen_random_uuid(),
    research_batch_id TEXT NOT NULL DEFAULT 'DEFAULT',
    research_code TEXT NOT NULL,
    strategy_code TEXT NOT NULL,
    strategy_version TEXT NOT NULL DEFAULT 'v1',
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    parameter_hash TEXT NOT NULL DEFAULT 'default',
    parameter_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    dataset_version TEXT NOT NULL DEFAULT 'default',
    runner_version TEXT NOT NULL DEFAULT 'EDGE_LAB_FOUNDATION_V1',
    status_code TEXT NOT NULL DEFAULT 'QUEUED',
    source_version TEXT NOT NULL DEFAULT 'EDGE_LAB_FOUNDATION_V1',
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(research_code, strategy_code, symbol, timeframe, parameter_hash, dataset_version)
);

CREATE TABLE IF NOT EXISTS analytics.edge_observation_v1 (
    id BIGSERIAL PRIMARY KEY,
    observation_uuid UUID NOT NULL DEFAULT gen_random_uuid(),
    run_uuid UUID NOT NULL,
    research_batch_id TEXT NOT NULL DEFAULT 'DEFAULT',
    research_code TEXT NOT NULL,
    strategy_code TEXT NOT NULL,
    strategy_version TEXT NOT NULL DEFAULT 'v1',
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    parameter_hash TEXT NOT NULL DEFAULT 'default',
    parameter_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    dataset_version TEXT NOT NULL DEFAULT 'default',
    market_data_version TEXT NOT NULL DEFAULT 'default',
    runner_version TEXT NOT NULL DEFAULT 'unknown',
    score_formula_version TEXT NOT NULL DEFAULT 'unknown',
    market_regime TEXT NOT NULL DEFAULT 'UNKNOWN',
    bars_used INTEGER NOT NULL DEFAULT 0,
    trades INTEGER NOT NULL DEFAULT 0,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    win_rate NUMERIC(12,6) NOT NULL DEFAULT 0,
    profit_factor NUMERIC(12,6) NOT NULL DEFAULT 0,
    expectancy NUMERIC(20,8) NOT NULL DEFAULT 0,
    avg_win NUMERIC(20,8) NOT NULL DEFAULT 0,
    avg_loss NUMERIC(20,8) NOT NULL DEFAULT 0,
    max_drawdown NUMERIC(20,8) NOT NULL DEFAULT 0,
    recovery_factor NUMERIC(12,6) NOT NULL DEFAULT 0,
    sharpe NUMERIC(12,6) NOT NULL DEFAULT 0,
    sortino NUMERIC(12,6) NOT NULL DEFAULT 0,
    ulcer_index NUMERIC(12,6) NOT NULL DEFAULT 0,
    commission NUMERIC(20,8) NOT NULL DEFAULT 0,
    slippage NUMERIC(20,8) NOT NULL DEFAULT 0,
    stability_score NUMERIC(12,6) NOT NULL DEFAULT 0,
    raw_edge_score NUMERIC(12,6) NOT NULL DEFAULT 0,
    normalized_edge_score NUMERIC(12,6) NOT NULL DEFAULT 0,
    confidence_score NUMERIC(12,6) NOT NULL DEFAULT 0,
    research_cost_score NUMERIC(12,6) NOT NULL DEFAULT 0,
    research_cpu_ms BIGINT NOT NULL DEFAULT 0,
    research_memory_mb NUMERIC(12,4) NOT NULL DEFAULT 0,
    research_elapsed_ms BIGINT NOT NULL DEFAULT 0,
    verdict_code TEXT NOT NULL DEFAULT 'OBSERVED',
    source_version TEXT NOT NULL DEFAULT 'EDGE_LAB_FOUNDATION_V1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(run_uuid)
);

CREATE TABLE IF NOT EXISTS analytics.edge_candidate_v1 (
    id BIGSERIAL PRIMARY KEY,
    candidate_uuid UUID NOT NULL DEFAULT gen_random_uuid(),
    observation_uuid UUID NOT NULL,
    research_batch_id TEXT NOT NULL DEFAULT 'DEFAULT',
    research_code TEXT NOT NULL,
    strategy_code TEXT NOT NULL,
    strategy_version TEXT NOT NULL DEFAULT 'v1',
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    parameter_hash TEXT NOT NULL DEFAULT 'default',
    parameter_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    dataset_version TEXT NOT NULL DEFAULT 'default',
    raw_edge_score NUMERIC(12,6) NOT NULL DEFAULT 0,
    normalized_edge_score NUMERIC(12,6) NOT NULL DEFAULT 0,
    confidence_score NUMERIC(12,6) NOT NULL DEFAULT 0,
    stability_score NUMERIC(12,6) NOT NULL DEFAULT 0,
    candidate_status TEXT NOT NULL DEFAULT 'EDGE_CANDIDATE',
    validation_stage TEXT NOT NULL DEFAULT 'NOT_STARTED',
    paper_allowed BOOLEAN NOT NULL DEFAULT false,
    shadow_allowed BOOLEAN NOT NULL DEFAULT false,
    micro_live_allowed BOOLEAN NOT NULL DEFAULT false,
    live_allowed BOOLEAN NOT NULL DEFAULT false,
    approved_at TIMESTAMPTZ,
    source_version TEXT NOT NULL DEFAULT 'EDGE_LAB_FOUNDATION_V1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(observation_uuid)
);

CREATE INDEX IF NOT EXISTS ix_edge_lab_run_v1_status ON analytics.edge_lab_run_v1(status_code);
CREATE INDEX IF NOT EXISTS ix_edge_lab_run_v1_research_code ON analytics.edge_lab_run_v1(research_code);
CREATE INDEX IF NOT EXISTS ix_edge_observation_v1_strategy_symbol ON analytics.edge_observation_v1(strategy_code, symbol, timeframe);
CREATE INDEX IF NOT EXISTS ix_edge_observation_v1_verdict ON analytics.edge_observation_v1(verdict_code);
CREATE INDEX IF NOT EXISTS ix_edge_candidate_v1_status ON analytics.edge_candidate_v1(candidate_status);

GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.edge_lab_run_v1 TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.edge_observation_v1 TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.edge_candidate_v1 TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO alex;
