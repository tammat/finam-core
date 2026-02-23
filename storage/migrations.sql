-- Finam_Core (v1) - Production-grade baseline schema for Event Engine + OMS + Accounting + Risk
-- Notes:
-- 1) All identifiers used by Python domain objects are stored as TEXT (uuid4 rendered to str).
-- 2) Time is stored as TIMESTAMPTZ.
-- 3) This file is safe to run on an empty DB. If tables already exist, it will not drop/alter them.

BEGIN;

-- ===============================
-- EXTENSIONS
-- ===============================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===============================
-- MARKET DATA (bars)
-- ===============================
CREATE TABLE IF NOT EXISTS market_data (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL DEFAULT '1m',
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close_price DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION NOT NULL DEFAULT 0,
    ts TIMESTAMPTZ NOT NULL,
    UNIQUE(symbol, timeframe, ts)
);

CREATE INDEX IF NOT EXISTS idx_market_data_symbol_ts
    ON market_data(symbol, ts DESC);

CREATE INDEX IF NOT EXISTS idx_market_data_ts
    ON market_data(ts DESC);

-- Optional: tick-level stream (for future)
CREATE TABLE IF NOT EXISTS market_ticks (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION NOT NULL DEFAULT 0,
    ts TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_market_ticks_symbol_ts
    ON market_ticks(symbol, ts DESC);

-- ===============================
-- SIGNALS (strategy output)
-- ===============================
CREATE TABLE IF NOT EXISTS signals (
    signal_id TEXT PRIMARY KEY,
    correlation_id TEXT,
    strategy TEXT NOT NULL,
    symbol TEXT NOT NULL,
    signal_type TEXT NOT NULL, -- e.g. LONG/SHORT/BUY/SELL
    strength DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    ts TIMESTAMPTZ NOT NULL,
    processed BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_signals_symbol_ts
    ON signals(symbol, ts DESC);

CREATE INDEX IF NOT EXISTS idx_signals_processed_ts
    ON signals(processed, ts DESC);

-- ===============================
-- SIGNAL FEATURES (feature store at decision time)
-- ===============================
CREATE TABLE IF NOT EXISTS signal_features (
    id BIGSERIAL PRIMARY KEY,
    signal_id TEXT NOT NULL REFERENCES signals(signal_id) ON DELETE CASCADE,
    feature_name TEXT NOT NULL,
    feature_value DOUBLE PRECISION,
    ts TIMESTAMPTZ NOT NULL,
    UNIQUE(signal_id, feature_name)
);

CREATE INDEX IF NOT EXISTS idx_signal_features_signal_id
    ON signal_features(signal_id);

-- ===============================
-- ORDERS (OMS)
-- ===============================
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    signal_event_id TEXT REFERENCES signals(signal_id) ON DELETE SET NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL, -- BUY/SELL
    qty DOUBLE PRECISION NOT NULL,
    filled_qty DOUBLE PRECISION NOT NULL DEFAULT 0,
    limit_price DOUBLE PRECISION,
    stop_price DOUBLE PRECISION,
    status TEXT NOT NULL, -- NEW/WORKING/FILLED/CANCELLED/REJECTED
    exchange_order_id TEXT,
    created_ts TIMESTAMPTZ NOT NULL,
    updated_ts TIMESTAMPTZ NOT NULL,
    raw_json JSONB
);

CREATE INDEX IF NOT EXISTS idx_orders_symbol_created
    ON orders(symbol, created_ts DESC);

CREATE INDEX IF NOT EXISTS idx_orders_status_updated
    ON orders(status, updated_ts DESC);

-- ===============================
-- FILLS (execution results)
-- ===============================
CREATE TABLE IF NOT EXISTS fills (
    fill_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    qty DOUBLE PRECISION NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    commission DOUBLE PRECISION NOT NULL DEFAULT 0,
    ts TIMESTAMPTZ NOT NULL,
    raw_json JSONB
);

CREATE INDEX IF NOT EXISTS idx_fills_order_id
    ON fills(order_id);

CREATE INDEX IF NOT EXISTS idx_fills_symbol_ts
    ON fills(symbol, ts DESC);

-- ===============================
-- POSITIONS (current state)
-- ===============================
CREATE TABLE IF NOT EXISTS positions (
    symbol TEXT PRIMARY KEY,
    qty DOUBLE PRECISION NOT NULL,
    avg_price DOUBLE PRECISION NOT NULL,
    realized_pnl DOUBLE PRECISION NOT NULL DEFAULT 0,
    unrealized_pnl DOUBLE PRECISION NOT NULL DEFAULT 0,
    exposure DOUBLE PRECISION NOT NULL DEFAULT 0,
    updated_ts TIMESTAMPTZ NOT NULL
);

-- Point-in-time position snapshots
CREATE TABLE IF NOT EXISTS positions_history (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    qty DOUBLE PRECISION NOT NULL,
    avg_price DOUBLE PRECISION NOT NULL,
    realized_pnl DOUBLE PRECISION NOT NULL,
    unrealized_pnl DOUBLE PRECISION NOT NULL,
    exposure DOUBLE PRECISION NOT NULL,
    ts TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_positions_history_symbol_ts
    ON positions_history(symbol, ts DESC);

-- ===============================
-- PORTFOLIO SNAPSHOTS (accounting state)
-- ===============================
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id BIGSERIAL PRIMARY KEY,
    equity DOUBLE PRECISION NOT NULL,
    cash DOUBLE PRECISION NOT NULL,
    margin_used DOUBLE PRECISION NOT NULL DEFAULT 0,
    exposure DOUBLE PRECISION NOT NULL DEFAULT 0,
    drawdown DOUBLE PRECISION NOT NULL DEFAULT 0,
    ts TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_ts
    ON portfolio_snapshots(ts DESC);

-- ===============================
-- RISK EVENTS (decisions + audit trail)
-- ===============================
CREATE TABLE IF NOT EXISTS risk_events (
    id BIGSERIAL PRIMARY KEY,
    event_id TEXT,
    symbol TEXT,
    rule_name TEXT NOT NULL,
    decision TEXT NOT NULL, -- ALLOW/BLOCK/WARN
    reason TEXT,
    ts TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_risk_events_ts
    ON risk_events(ts DESC);

CREATE INDEX IF NOT EXISTS idx_risk_events_symbol_ts
    ON risk_events(symbol, ts DESC);

-- ===============================
-- ENGINE METRICS (perf + counters)
-- ===============================
CREATE TABLE IF NOT EXISTS engine_metrics (
    id BIGSERIAL PRIMARY KEY,
    metric_name TEXT NOT NULL,
    metric_value DOUBLE PRECISION,
    ts TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_engine_metrics_name_ts
    ON engine_metrics(metric_name, ts DESC);

-- ===============================
-- MODEL REGISTRY + INFERENCE LOG (AI-ready)
-- ===============================
CREATE TABLE IF NOT EXISTS model_registry (
    model_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    version TEXT NOT NULL,
    artifact_uri TEXT,
    sha256 TEXT,
    created_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
    meta JSONB
);

CREATE INDEX IF NOT EXISTS idx_model_registry_name_version
    ON model_registry(name, version);

CREATE TABLE IF NOT EXISTS inference_log (
    id BIGSERIAL PRIMARY KEY,
    model_id TEXT REFERENCES model_registry(model_id) ON DELETE SET NULL,
    correlation_id TEXT,
    symbol TEXT,
    features JSONB,
    prediction JSONB,
    ts TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_inference_log_symbol_ts
    ON inference_log(symbol, ts DESC);

-- ===============================
-- TRADES / TRANSACTIONS (optional import/export layer)
-- ===============================
CREATE TABLE IF NOT EXISTS trades (
    trade_id TEXT PRIMARY KEY,
    account_id TEXT,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    qty DOUBLE PRECISION NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    commission DOUBLE PRECISION NOT NULL DEFAULT 0,
    ts TIMESTAMPTZ NOT NULL,
    raw_json JSONB
);

CREATE INDEX IF NOT EXISTS idx_trades_symbol_ts
    ON trades(symbol, ts DESC);

CREATE TABLE IF NOT EXISTS transactions (
    txn_id TEXT PRIMARY KEY,
    account_id TEXT,
    kind TEXT NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    currency TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    raw_json JSONB
);
CREATE TABLE IF NOT EXISTS stream_snapshots (
    id BIGSERIAL PRIMARY KEY,
    stream TEXT NOT NULL,
    last_seq BIGINT NOT NULL,
    state JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(stream, last_seq)
);

CREATE INDEX IF NOT EXISTS idx_snapshots_stream
ON stream_snapshots(stream);

CREATE INDEX IF NOT EXISTS idx_snapshots_last_seq
ON stream_snapshots(last_seq);
CREATE INDEX IF NOT EXISTS idx_transactions_ts
    ON transactions(ts DESC);

COMMIT;