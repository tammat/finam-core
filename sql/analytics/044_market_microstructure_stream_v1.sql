CREATE TABLE IF NOT EXISTS analytics.market_microstructure_snapshot_v1 (
    snapshot_id BIGSERIAL PRIMARY KEY,
    observed_at TIMESTAMPTZ NOT NULL,
    exchange_ts TIMESTAMPTZ,
    symbol TEXT NOT NULL,
    best_bid NUMERIC,
    best_ask NUMERIC,
    bid_size NUMERIC,
    ask_size NUMERIC,
    spread NUMERIC,
    spread_bps NUMERIC,
    bid_depth NUMERIC NOT NULL DEFAULT 0,
    ask_depth NUMERIC NOT NULL DEFAULT 0,
    imbalance NUMERIC,
    bid_levels INTEGER NOT NULL DEFAULT 0,
    ask_levels INTEGER NOT NULL DEFAULT 0,
    source_latency_ms NUMERIC,
    source_code TEXT NOT NULL,
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_market_microstructure_symbol_observed_v1
ON analytics.market_microstructure_snapshot_v1(symbol, observed_at DESC);

CREATE TABLE IF NOT EXISTS analytics.market_trade_tape_v1 (
    symbol TEXT NOT NULL,
    trade_id TEXT NOT NULL,
    exchange_ts TIMESTAMPTZ NOT NULL,
    price NUMERIC NOT NULL,
    size NUMERIC NOT NULL,
    side_code TEXT NOT NULL,
    mpid TEXT NOT NULL DEFAULT '',
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source_code TEXT NOT NULL,
    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY(symbol, trade_id)
);

CREATE INDEX IF NOT EXISTS idx_market_trade_tape_symbol_ts_v1
ON analytics.market_trade_tape_v1(symbol, exchange_ts DESC);

CREATE OR REPLACE VIEW analytics.market_microstructure_quality_v1 AS
SELECT
    symbol,
    count(*) AS snapshots,
    count(DISTINCT (observed_at AT TIME ZONE 'Europe/Moscow')::date) AS trading_days,
    min(observed_at) AS first_observed_at,
    max(observed_at) AS last_observed_at,
    extract(epoch FROM (now()-max(observed_at))) AS latest_age_seconds,
    count(*) FILTER (WHERE best_bid IS NULL OR best_ask IS NULL) AS incomplete_snapshots,
    count(*) FILTER (WHERE best_bid >= best_ask) AS crossed_snapshots,
    count(*) FILTER (WHERE bid_levels=0 OR ask_levels=0) AS empty_book_snapshots,
    CASE
        WHEN count(DISTINCT (observed_at AT TIME ZONE 'Europe/Moscow')::date) >= 20
         AND count(*) >= 10000
         AND count(*) FILTER (WHERE best_bid IS NULL OR best_ask IS NULL OR best_bid >= best_ask)=0
        THEN 'QUOTE_VERIFIED'
        ELSE 'COLLECTING'
    END AS market_data_quality
FROM analytics.market_microstructure_snapshot_v1
GROUP BY symbol;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='finam') THEN
        GRANT SELECT, INSERT ON analytics.market_microstructure_snapshot_v1 TO finam;
        GRANT USAGE, SELECT ON SEQUENCE analytics.market_microstructure_snapshot_v1_snapshot_id_seq TO finam;
        GRANT SELECT, INSERT, UPDATE ON analytics.market_trade_tape_v1 TO finam;
        GRANT SELECT ON analytics.market_microstructure_quality_v1 TO finam;
    END IF;
END $$;
