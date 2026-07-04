CREATE TABLE IF NOT EXISTS analytics.strategy_signal_snapshot_v1 (
    id BIGSERIAL PRIMARY KEY,

    symbol TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    asset_class TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL,
    strategy_family TEXT NOT NULL,
    signal_ts TIMESTAMPTZ NOT NULL,

    signal_direction TEXT NOT NULL DEFAULT 'FLAT',
    signal_strength NUMERIC(20,6) NOT NULL DEFAULT 0,
    signal_score NUMERIC(20,6) NOT NULL DEFAULT 0,
    confidence NUMERIC(20,6) NOT NULL DEFAULT 0,
    signal_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    feature_quality_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    market_quality_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    paper_allowed BOOLEAN NOT NULL DEFAULT false,
    risk_allowed BOOLEAN NOT NULL DEFAULT false,
    execution_allowed BOOLEAN NOT NULL DEFAULT false,

    feature_version TEXT NOT NULL DEFAULT 'FEATURE_STORE_V1',
    strategy_version TEXT NOT NULL DEFAULT 'MULTI_STRATEGY_ENGINE_SCHEMA_V1',
    source_table TEXT NOT NULL DEFAULT 'analytics.feature_snapshot_v1',
    build_id TEXT NOT NULL DEFAULT 'manual',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_strategy_signal_snapshot_v1
        UNIQUE (symbol, timeframe, strategy_family, signal_ts)
);

CREATE INDEX IF NOT EXISTS ix_strategy_signal_snapshot_v1_symbol_tf_ts
ON analytics.strategy_signal_snapshot_v1(symbol, timeframe, signal_ts DESC);

CREATE INDEX IF NOT EXISTS ix_strategy_signal_snapshot_v1_strategy
ON analytics.strategy_signal_snapshot_v1(strategy_family);

CREATE INDEX IF NOT EXISTS ix_strategy_signal_snapshot_v1_score
ON analytics.strategy_signal_snapshot_v1(signal_score DESC);

CREATE INDEX IF NOT EXISTS ix_strategy_signal_snapshot_v1_status
ON analytics.strategy_signal_snapshot_v1(signal_status);

GRANT USAGE ON SCHEMA analytics TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA analytics TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO alex;
