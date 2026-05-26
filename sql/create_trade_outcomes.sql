CREATE TABLE IF NOT EXISTS trade_outcomes (
    id BIGSERIAL PRIMARY KEY,

    entry_trade_id BIGINT NOT NULL,
    exit_trade_id BIGINT NOT NULL,

    entry_fill_id TEXT,
    exit_fill_id TEXT,

    symbol TEXT NOT NULL,
    continuous_symbol TEXT,
    strategy TEXT,
    timeframe TEXT,
    trade_source TEXT NOT NULL DEFAULT 'paper',

    entry_side TEXT NOT NULL,
    exit_side TEXT NOT NULL,
    qty DOUBLE PRECISION NOT NULL,

    entry_price DOUBLE PRECISION NOT NULL,
    exit_price DOUBLE PRECISION NOT NULL,

    gross_pnl DOUBLE PRECISION NOT NULL,
    commission DOUBLE PRECISION NOT NULL DEFAULT 0,
    net_pnl DOUBLE PRECISION NOT NULL,

    entry_ts TIMESTAMPTZ,
    exit_ts TIMESTAMPTZ,
    holding_seconds DOUBLE PRECISION,

    run_id TEXT,
    outcome_source TEXT NOT NULL DEFAULT 'trade_outcome_engine_v1',
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(entry_trade_id, exit_trade_id)
);

CREATE INDEX IF NOT EXISTS idx_trade_outcomes_symbol_exit
ON trade_outcomes(symbol, exit_ts DESC);

CREATE INDEX IF NOT EXISTS idx_trade_outcomes_continuous_symbol_exit
ON trade_outcomes(continuous_symbol, exit_ts DESC);

CREATE INDEX IF NOT EXISTS idx_trade_outcomes_strategy_tf
ON trade_outcomes(strategy, timeframe);
