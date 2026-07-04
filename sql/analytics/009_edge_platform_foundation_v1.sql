CREATE TABLE IF NOT EXISTS analytics.edge_decision_snapshot_v1 (

    id BIGSERIAL PRIMARY KEY,

    signal_id BIGINT,

    symbol TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    timeframe TEXT NOT NULL,

    strategy_family TEXT NOT NULL,
    strategy_version TEXT NOT NULL,

    signal_ts TIMESTAMPTZ NOT NULL,

    edge_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    validation_score NUMERIC(10,4) NOT NULL DEFAULT 0,
    governance_score NUMERIC(10,4) NOT NULL DEFAULT 0,

    decision_code TEXT NOT NULL DEFAULT 'BLOCK',
    recommendation_code TEXT NOT NULL DEFAULT 'WAIT_RESEARCH',

    ready_for_research BOOLEAN NOT NULL DEFAULT false,
    ready_for_replay BOOLEAN NOT NULL DEFAULT false,
    ready_for_paper BOOLEAN NOT NULL DEFAULT false,
    ready_for_shadow BOOLEAN NOT NULL DEFAULT false,
    ready_for_micro_live BOOLEAN NOT NULL DEFAULT false,
    ready_for_live BOOLEAN NOT NULL DEFAULT false,

    source_version TEXT NOT NULL DEFAULT 'EDGE_PLATFORM_FOUNDATION_V1',
    build_id TEXT NOT NULL DEFAULT 'manual',

    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(symbol,timeframe,strategy_family,signal_ts)
);

CREATE INDEX IF NOT EXISTS ix_edge_snapshot_symbol
ON analytics.edge_decision_snapshot_v1(symbol);

CREATE INDEX IF NOT EXISTS ix_edge_snapshot_strategy
ON analytics.edge_decision_snapshot_v1(strategy_family);

CREATE INDEX IF NOT EXISTS ix_edge_snapshot_decision
ON analytics.edge_decision_snapshot_v1(decision_code);



CREATE TABLE IF NOT EXISTS analytics.edge_configuration_v1 (

    edge_name TEXT PRIMARY KEY,

    enabled BOOLEAN NOT NULL DEFAULT true,

    config_json JSONB NOT NULL DEFAULT '{}'::jsonb,

    source_version TEXT NOT NULL DEFAULT 'EDGE_PLATFORM_FOUNDATION_V1',

    build_id TEXT NOT NULL DEFAULT 'manual',

    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);



CREATE TABLE IF NOT EXISTS analytics.edge_governance_v1 (

    governance_scope TEXT PRIMARY KEY,

    score_engine_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    validation_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    decision_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    api_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    ui_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    governance_score NUMERIC(10,4) NOT NULL DEFAULT 0,

    readiness_code TEXT NOT NULL DEFAULT 'NOT_READY',

    recommendation_code TEXT NOT NULL DEFAULT 'WAIT_RESEARCH',

    source_version TEXT NOT NULL DEFAULT 'EDGE_PLATFORM_FOUNDATION_V1',

    build_id TEXT NOT NULL DEFAULT 'manual',

    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);



INSERT INTO analytics.edge_configuration_v1 (

    edge_name,
    enabled,
    config_json

)

VALUES (

    'DEFAULT',

    true,

    '{
        "min_edge_score":0.60,
        "min_validation_score":0.70,
        "min_governance_score":0.90
    }'::jsonb

)

ON CONFLICT(edge_name)

DO UPDATE

SET

config_json=excluded.config_json,

updated_at=now();



GRANT USAGE ON SCHEMA analytics TO alex;

GRANT SELECT,INSERT,UPDATE,DELETE
ON ALL TABLES IN SCHEMA analytics
TO alex;
