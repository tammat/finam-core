CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.edge_oos_result_v1 (
    id BIGSERIAL PRIMARY KEY,
    observation_uuid UUID NOT NULL,
    research_batch_id TEXT NOT NULL,
    strategy_code TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    parameter_hash TEXT NOT NULL,
    parameter_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    validation_version TEXT NOT NULL,
    in_sample_bars INTEGER NOT NULL,
    oos_bars INTEGER NOT NULL,
    oos_start TIMESTAMPTZ NOT NULL,
    oos_end TIMESTAMPTZ NOT NULL,
    oos_trades INTEGER NOT NULL,
    oos_profit_factor NUMERIC NOT NULL,
    oos_expectancy NUMERIC NOT NULL,
    oos_max_drawdown NUMERIC NOT NULL,
    folds_total INTEGER NOT NULL,
    folds_passed INTEGER NOT NULL,
    verdict_code TEXT NOT NULL CHECK (verdict_code IN ('OOS_PASS','OOS_FAIL')),
    promotion_allowed BOOLEAN NOT NULL DEFAULT false,
    reason TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (observation_uuid, validation_version)
);

CREATE INDEX IF NOT EXISTS edge_oos_result_v1_verdict_idx
    ON analytics.edge_oos_result_v1 (verdict_code, updated_at DESC);
