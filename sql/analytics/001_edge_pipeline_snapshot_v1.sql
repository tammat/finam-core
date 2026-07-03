CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.edge_pipeline_snapshot_v1 (
    id BIGSERIAL PRIMARY KEY,

    symbol TEXT NOT NULL DEFAULT '',
    display_name TEXT NOT NULL DEFAULT '',
    asset_class TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL DEFAULT '',
    strategy_family TEXT NOT NULL DEFAULT '',

    pipeline_stage SMALLINT NOT NULL DEFAULT 10,
    overall_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    ranking_score NUMERIC(20,6) NOT NULL DEFAULT 0,
    research_priority TEXT NOT NULL DEFAULT 'UNKNOWN',
    research_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    validation_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    validation_score NUMERIC(20,6) NOT NULL DEFAULT 0,

    robustness_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    robustness_score NUMERIC(20,6) NOT NULL DEFAULT 0,

    oos_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    oos_score NUMERIC(20,6) NOT NULL DEFAULT 0,

    backtest_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    backtest_score NUMERIC(20,6) NOT NULL DEFAULT 0,

    paper_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    paper_progress NUMERIC(10,2) NOT NULL DEFAULT 0,
    paper_trades INTEGER NOT NULL DEFAULT 0,

    risk_status TEXT NOT NULL DEFAULT 'NOT_READY',
    trading_status TEXT NOT NULL DEFAULT 'NOT_READY',
    runtime_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    source_version TEXT NOT NULL DEFAULT 'EDGE_PIPELINE_V2_SCHEMA_V1',
    build_id TEXT NOT NULL DEFAULT 'manual',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_edge_pipeline_snapshot_v1_candidate
        UNIQUE (symbol, timeframe, strategy_family)
);

CREATE INDEX IF NOT EXISTS ix_edge_pipeline_snapshot_v1_symbol_tf
ON analytics.edge_pipeline_snapshot_v1(symbol, timeframe);

CREATE INDEX IF NOT EXISTS ix_edge_pipeline_snapshot_v1_stage
ON analytics.edge_pipeline_snapshot_v1(pipeline_stage);

CREATE INDEX IF NOT EXISTS ix_edge_pipeline_snapshot_v1_overall_status
ON analytics.edge_pipeline_snapshot_v1(overall_status);

CREATE INDEX IF NOT EXISTS ix_edge_pipeline_snapshot_v1_strategy_family
ON analytics.edge_pipeline_snapshot_v1(strategy_family);

CREATE INDEX IF NOT EXISTS ix_edge_pipeline_snapshot_v1_research_priority
ON analytics.edge_pipeline_snapshot_v1(research_priority);

GRANT USAGE ON SCHEMA analytics TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA analytics TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO alex;

ALTER DEFAULT PRIVILEGES IN SCHEMA analytics
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO alex;

ALTER DEFAULT PRIVILEGES IN SCHEMA analytics
GRANT USAGE, SELECT ON SEQUENCES TO alex;
