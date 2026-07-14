CREATE TABLE IF NOT EXISTS analytics.market_tick_aggregate_v1 (
    interval_code TEXT NOT NULL,
    bucket_ts TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    open_price NUMERIC NOT NULL,
    high_price NUMERIC NOT NULL,
    low_price NUMERIC NOT NULL,
    close_price NUMERIC NOT NULL,
    volume NUMERIC NOT NULL,
    event_count BIGINT NOT NULL,
    source_version TEXT NOT NULL,
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY(interval_code,bucket_ts,symbol)
);

CREATE TABLE IF NOT EXISTS analytics.market_microstructure_aggregate_v1 (
    interval_code TEXT NOT NULL,
    bucket_ts TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    avg_best_bid NUMERIC,
    avg_best_ask NUMERIC,
    avg_spread_bps NUMERIC,
    max_spread_bps NUMERIC,
    avg_bid_depth NUMERIC,
    avg_ask_depth NUMERIC,
    avg_imbalance NUMERIC,
    snapshot_count BIGINT NOT NULL,
    source_version TEXT NOT NULL,
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY(interval_code,bucket_ts,symbol)
);

CREATE INDEX IF NOT EXISTS idx_microstructure_observed_brin_v1
ON analytics.market_microstructure_snapshot_v1 USING brin(observed_at);

GRANT SELECT,INSERT,UPDATE,DELETE ON analytics.market_tick_aggregate_v1 TO finam;
GRANT SELECT,INSERT,UPDATE,DELETE ON analytics.market_microstructure_aggregate_v1 TO finam;
