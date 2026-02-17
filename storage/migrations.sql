-- Trades
CREATE TABLE IF NOT EXISTS trades (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT,
    side TEXT,
    quantity DOUBLE PRECISION,
    price DOUBLE PRECISION,
    ts TIMESTAMPTZ
);

-- Orders
CREATE TABLE IF NOT EXISTS orders (
    id BIGSERIAL PRIMARY KEY,
    order_id TEXT UNIQUE,
    symbol TEXT,
    side TEXT,
    quantity DOUBLE PRECISION,
    status TEXT,
    ts TIMESTAMPTZ
);
-- Market ticks
CREATE TABLE IF NOT EXISTS market_ticks (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT,
    price DOUBLE PRECISION,
    volume DOUBLE PRECISION,
    ts TIMESTAMPTZ
);

-- Signals
CREATE TABLE IF NOT EXISTS signals (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT,
    signal_type TEXT,
    strength DOUBLE PRECISION,
    ts TIMESTAMPTZ
);

-- Risk events
CREATE TABLE IF NOT EXISTS risk_events (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT,
    reason TEXT,
    ts TIMESTAMPTZ
);

-- Historical prices
CREATE TABLE IF NOT EXISTS historical_prices (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    close DOUBLE PRECISION NOT NULL,
    volume DOUBLE PRECISION,
    UNIQUE(symbol, ts)
);

CREATE INDEX IF NOT EXISTS idx_hist_symbol_ts
ON historical_prices(symbol, ts);
-- Feature store
CREATE TABLE IF NOT EXISTS features (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    feature_name TEXT NOT NULL,
    feature_value DOUBLE PRECISION,
    UNIQUE(symbol, ts, feature_name)
);

CREATE INDEX IF NOT EXISTS idx_features_symbol_ts
ON features(symbol, ts);
-- Model registry
CREATE TABLE IF NOT EXISTS model_registry (
    id BIGSERIAL PRIMARY KEY,
    model_name TEXT NOT NULL,
    version TEXT NOT NULL,
    dataset_path TEXT NOT NULL,
    features JSONB NOT NULL,
    threshold DOUBLE PRECISION,
    metrics JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(model_name, version)
);
-- Inference log
CREATE TABLE IF NOT EXISTS inference_log (
    id BIGSERIAL PRIMARY KEY,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    symbol TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    probability DOUBLE PRECISION NOT NULL,
    predicted_label TEXT NOT NULL,
    features JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inference_symbol_ts
ON inference_log(symbol, ts);