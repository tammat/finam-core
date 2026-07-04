CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.feature_snapshot_v1 (
    symbol TEXT NOT NULL,
    asset_class TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL,
    bar_ts TIMESTAMPTZ NOT NULL,

    open NUMERIC(20,8),
    high NUMERIC(20,8),
    low NUMERIC(20,8),
    close NUMERIC(20,8),
    volume NUMERIC(20,4),

    range_abs NUMERIC(20,8),
    range_pct NUMERIC(20,8),
    body_abs NUMERIC(20,8),
    body_pct NUMERIC(20,8),
    upper_wick_pct NUMERIC(20,8),
    lower_wick_pct NUMERIC(20,8),

    hour_msk INTEGER,
    weekday_msk INTEGER,

    freshness_sec INTEGER,
    market_quality_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    feature_quality_score NUMERIC(10,4) NOT NULL DEFAULT 0,

    source_table TEXT NOT NULL DEFAULT 'marketcore.market_snapshot_v1',
    source_version TEXT NOT NULL DEFAULT 'FEATURE_STORE_V1',
    build_id TEXT NOT NULL DEFAULT 'manual',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (symbol, timeframe, bar_ts)
);

CREATE INDEX IF NOT EXISTS ix_feature_snapshot_v1_symbol_tf_ts
ON analytics.feature_snapshot_v1(symbol, timeframe, bar_ts DESC);

CREATE INDEX IF NOT EXISTS ix_feature_snapshot_v1_quality
ON analytics.feature_snapshot_v1(feature_quality_score DESC);

GRANT USAGE ON SCHEMA analytics TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA analytics TO alex;
