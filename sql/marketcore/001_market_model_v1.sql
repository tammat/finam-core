CREATE SCHEMA IF NOT EXISTS marketcore;

CREATE TABLE IF NOT EXISTS marketcore.market_snapshot_v1 (
    symbol TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    asset_class TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL,
    bar_ts TIMESTAMPTZ NOT NULL,
    open NUMERIC(20,8),
    high NUMERIC(20,8),
    low NUMERIC(20,8),
    close NUMERIC(20,8),
    volume NUMERIC(20,4),
    freshness_sec INTEGER,
    quality_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    source_table TEXT NOT NULL DEFAULT 'public.market_bars',
    source_version TEXT NOT NULL DEFAULT 'MARKET_MODEL_V1',
    build_id TEXT NOT NULL DEFAULT 'manual',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (symbol, timeframe, bar_ts)
);

CREATE INDEX IF NOT EXISTS ix_market_snapshot_v1_symbol_tf_ts
ON marketcore.market_snapshot_v1(symbol, timeframe, bar_ts DESC);
