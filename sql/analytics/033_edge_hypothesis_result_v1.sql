CREATE TABLE IF NOT EXISTS analytics.edge_hypothesis_result_v1 (
    id BIGSERIAL PRIMARY KEY,
    discovery_run_id UUID NOT NULL,
    strategy_family TEXT NOT NULL,
    strategy_code TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    parameter_json JSONB NOT NULL,
    market_regimes JSONB NOT NULL,
    validation_trades INTEGER NOT NULL,
    validation_profit_factor NUMERIC NOT NULL,
    validation_expectancy NUMERIC NOT NULL,
    oos_trades INTEGER NOT NULL,
    oos_profit_factor NUMERIC NOT NULL,
    oos_expectancy NUMERIC NOT NULL,
    oos_max_drawdown NUMERIC NOT NULL,
    folds_passed INTEGER NOT NULL,
    profitable_regimes INTEGER NOT NULL,
    transaction_cost_bps NUMERIC NOT NULL,
    hypothesis_score NUMERIC NOT NULL,
    verdict_code TEXT NOT NULL CHECK (verdict_code IN ('OOS_PASS','OOS_FAIL')),
    promotion_allowed BOOLEAN NOT NULL DEFAULT false,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (discovery_run_id,strategy_code,symbol,timeframe,parameter_json)
);

CREATE INDEX IF NOT EXISTS edge_hypothesis_result_v1_rank_idx
    ON analytics.edge_hypothesis_result_v1 (discovery_run_id,hypothesis_score DESC);
