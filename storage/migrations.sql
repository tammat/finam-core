-- ===============================
-- EXTENSIONS
-- ===============================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===============================
-- MARKET DATA
-- ===============================
CREATE TABLE IF NOT EXISTS market_data (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL DEFAULT '1m',
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION,
    ts TIMESTAMPTZ NOT NULL,
    UNIQUE(symbol, timeframe, ts)
);

CREATE INDEX IF NOT EXISTS idx_market_symbol_ts
ON market_data(symbol, ts DESC);

-- ===============================
-- SIGNALS
-- ===============================
CREATE TABLE IF NOT EXISTS signals (
    event_id UUID PRIMARY KEY,
    correlation_id UUID,
    strategy TEXT NOT NULL,
    symbol TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    strength DOUBLE PRECISION,
    ts TIMESTAMPTZ NOT NULL,
    processed BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_signals_symbol_ts
ON signals(symbol, ts DESC);

-- ===============================
-- SIGNAL FEATURES
-- ===============================
CREATE TABLE IF NOT EXISTS signal_features (
    id BIGSERIAL PRIMARY KEY,
    event_id UUID REFERENCES signals(event_id) ON DELETE CASCADE,
    feature_name TEXT NOT NULL,
    feature_value DOUBLE PRECISION,
    ts TIMESTAMPTZ NOT NULL
);

-- ===============================
-- ORDERS (OMS)
-- ===============================
CREATE TABLE IF NOT EXISTS orders (
    order_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    signal_event_id UUID REFERENCES signals(event_id),
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    qty DOUBLE PRECISION NOT NULL,
    limit_price DOUBLE PRECISION,
    stop_price DOUBLE PRECISION,
    status TEXT NOT NULL,
    exchange_order_id TEXT,
    created_ts TIMESTAMPTZ NOT NULL,
    updated_ts TIMESTAMPTZ NOT NULL,
    raw_json JSONB
);

CREATE INDEX IF NOT EXISTS idx_orders_symbol
ON orders(symbol);

-- ===============================
-- FILLS
-- ===============================
CREATE TABLE IF NOT EXISTS fills (
    fill_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID REFERENCES orders(order_id),
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    qty DOUBLE PRECISION NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    commission DOUBLE PRECISION DEFAULT 0,
    ts TIMESTAMPTZ NOT NULL,
    raw_json JSONB
);

CREATE INDEX IF NOT EXISTS idx_fills_symbol
ON fills(symbol);

-- ===============================
-- POSITIONS (CURRENT STATE)
-- ===============================
CREATE TABLE IF NOT EXISTS positions (
    symbol TEXT PRIMARY KEY,
    qty DOUBLE PRECISION NOT NULL,
    avg_price DOUBLE PRECISION NOT NULL,
    realized_pnl DOUBLE PRECISION NOT NULL DEFAULT 0,
    unrealized_pnl DOUBLE PRECISION NOT NULL DEFAULT 0,
    exposure DOUBLE PRECISION,
    updated_ts TIMESTAMPTZ NOT NULL
);

-- ===============================
-- POSITIONS HISTORY
-- ===============================
CREATE TABLE IF NOT EXISTS positions_history (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    qty DOUBLE PRECISION NOT NULL,
    avg_price DOUBLE PRECISION NOT NULL,
    realized_pnl DOUBLE PRECISION NOT NULL,
    unrealized_pnl DOUBLE PRECISION NOT NULL,
    exposure DOUBLE PRECISION,
    ts TIMESTAMPTZ NOT NULL
);

-- ===============================
-- PORTFOLIO SNAPSHOTS
-- ===============================
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id BIGSERIAL PRIMARY KEY,
    equity DOUBLE PRECISION NOT NULL,
    cash DOUBLE PRECISION NOT NULL,
    margin_used DOUBLE PRECISION,
    exposure DOUBLE PRECISION,
    drawdown DOUBLE PRECISION,
    ts TIMESTAMPTZ NOT NULL
);

-- ===============================
-- RISK EVENTS
-- ===============================
CREATE TABLE IF NOT EXISTS risk_events (
    id BIGSERIAL PRIMARY KEY,
    event_id UUID,
    symbol TEXT,
    rule_name TEXT NOT NULL,
    decision TEXT NOT NULL,
    reason TEXT,
    ts TIMESTAMPTZ NOT NULL
);

-- ===============================
-- ENGINE METRICS
-- ===============================
CREATE TABLE IF NOT EXISTS engine_metrics (
    id BIGSERIAL PRIMARY KEY,
    metric_name TEXT NOT NULL,
    metric_value DOUBLE PRECISION,
    ts TIMESTAMPTZ NOT NULL
);