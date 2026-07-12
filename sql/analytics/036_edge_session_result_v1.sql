CREATE TABLE IF NOT EXISTS analytics.edge_session_result_v1 (
    id BIGSERIAL PRIMARY KEY,
    discovery_run_id UUID NOT NULL,
    strategy_family TEXT NOT NULL,
    strategy_code TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    parameter_json JSONB NOT NULL,
    regime_code TEXT NOT NULL,
    session_code TEXT NOT NULL,
    session_timezone TEXT NOT NULL,
    regime_coverage_ratio NUMERIC NOT NULL,
    validation_trades INTEGER NOT NULL,
    validation_profit_factor NUMERIC NOT NULL,
    validation_expectancy NUMERIC NOT NULL,
    oos_trades INTEGER NOT NULL,
    oos_profit_factor NUMERIC NOT NULL,
    oos_expectancy NUMERIC NOT NULL,
    oos_max_drawdown NUMERIC NOT NULL,
    folds_passed INTEGER NOT NULL,
    folds_total INTEGER NOT NULL,
    raw_p_value NUMERIC NOT NULL,
    adjusted_p_value NUMERIC NOT NULL,
    trust_status TEXT NOT NULL CHECK (trust_status IN ('VERIFIED','UNVERIFIED')),
    verdict_code TEXT NOT NULL CHECK (verdict_code IN ('OOS_PASS','OOS_FAIL','UNVERIFIED')),
    reason_code TEXT NOT NULL,
    promotion_allowed BOOLEAN NOT NULL DEFAULT false,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (discovery_run_id,strategy_code,symbol,timeframe,parameter_json,regime_code,session_code)
);

CREATE INDEX IF NOT EXISTS edge_session_result_v1_rank_idx ON analytics.edge_session_result_v1
    (discovery_run_id,verdict_code,adjusted_p_value,oos_profit_factor DESC);
