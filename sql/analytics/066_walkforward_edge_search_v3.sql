BEGIN;
CREATE TABLE IF NOT EXISTS analytics.walkforward_edge_search_v3 (
    result_id UUID PRIMARY KEY,
    search_run_id UUID NOT NULL,
    strategy_family TEXT NOT NULL,
    strategy_code TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    parameter_json JSONB NOT NULL,
    transaction_cost_bps NUMERIC NOT NULL,
    total_trades INTEGER NOT NULL,
    net_profit_factor NUMERIC NOT NULL,
    net_expectancy NUMERIC NOT NULL,
    max_drawdown NUMERIC NOT NULL,
    folds_total INTEGER NOT NULL,
    folds_passed INTEGER NOT NULL,
    final_holdout_passed BOOLEAN NOT NULL,
    fold_metrics JSONB NOT NULL,
    verdict_code TEXT NOT NULL CHECK (verdict_code IN ('OOS_PASS','OOS_FAIL')),
    promotion_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    reason_code TEXT NOT NULL,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    UNIQUE(search_run_id,strategy_code,symbol,timeframe,parameter_json)
);
REVOKE INSERT,UPDATE,DELETE,TRUNCATE ON analytics.walkforward_edge_search_v3 FROM PUBLIC;
GRANT SELECT,INSERT,UPDATE ON analytics.walkforward_edge_search_v3 TO alex;
COMMIT;
