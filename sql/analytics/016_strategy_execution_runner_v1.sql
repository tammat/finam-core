CREATE TABLE IF NOT EXISTS analytics.research_trade_v1 (
    id BIGSERIAL PRIMARY KEY,
    run_uuid UUID NOT NULL,
    research_code TEXT NOT NULL,
    strategy_code TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    trade_no INTEGER NOT NULL,
    side TEXT NOT NULL,
    entry_ts TIMESTAMPTZ,
    exit_ts TIMESTAMPTZ,
    entry_price NUMERIC(20,8) NOT NULL DEFAULT 0,
    exit_price NUMERIC(20,8) NOT NULL DEFAULT 0,
    gross_pnl NUMERIC(20,8) NOT NULL DEFAULT 0,
    commission NUMERIC(20,8) NOT NULL DEFAULT 0,
    slippage NUMERIC(20,8) NOT NULL DEFAULT 0,
    net_pnl NUMERIC(20,8) NOT NULL DEFAULT 0,
    source_version TEXT NOT NULL DEFAULT 'STRATEGY_EXECUTION_RUNNER_V1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(run_uuid, trade_no)
);

CREATE INDEX IF NOT EXISTS ix_research_trade_v1_run_uuid
ON analytics.research_trade_v1(run_uuid);

CREATE INDEX IF NOT EXISTS ix_research_trade_v1_strategy_symbol
ON analytics.research_trade_v1(strategy_code, symbol, timeframe);

GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.research_trade_v1 TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO alex;
