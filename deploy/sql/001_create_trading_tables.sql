-- deploy/sql/001_create_trading_tables.sql
-- Русский коммент: базовые таблицы логирования PAPER/live pipeline.

CREATE TABLE IF NOT EXISTS trades (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    qty DOUBLE PRECISION NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    trade_id TEXT,
    execution_type TEXT,
    commission DOUBLE PRECISION DEFAULT 0
);

CREATE TABLE IF NOT EXISTS signals (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    symbol TEXT,
    strategy TEXT,
    side TEXT,
    qty DOUBLE PRECISION,
    status TEXT NOT NULL,
    payload JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS risk_events (
    id BIGSERIAL PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    symbol TEXT,
    event TEXT NOT NULL,
    decision TEXT,
    payload JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_trades_ts ON trades(ts);
CREATE INDEX IF NOT EXISTS idx_trades_symbol_ts ON trades(symbol, ts);
CREATE INDEX IF NOT EXISTS idx_signals_ts ON signals(ts);
CREATE INDEX IF NOT EXISTS idx_risk_events_ts ON risk_events(ts);
