CREATE TABLE IF NOT EXISTS analytics.strategy_platform_governance_v1 (
    governance_scope TEXT PRIMARY KEY DEFAULT 'GLOBAL',

    registry_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    configuration_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    dependency_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    builder_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    signal_store_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    api_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    ui_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    integrity_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    health_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    readiness_status TEXT NOT NULL DEFAULT 'NOT_READY',
    overall_status TEXT NOT NULL DEFAULT 'UNKNOWN',

    governance_score NUMERIC(10,4) NOT NULL DEFAULT 0,

    registry_rows INTEGER NOT NULL DEFAULT 0,
    enabled_strategies INTEGER NOT NULL DEFAULT 0,
    active_configs INTEGER NOT NULL DEFAULT 0,
    dependency_rows INTEGER NOT NULL DEFAULT 0,
    signal_rows INTEGER NOT NULL DEFAULT 0,
    unsafe_execution_rows INTEGER NOT NULL DEFAULT 0,
    missing_config_rows INTEGER NOT NULL DEFAULT 0,
    duplicate_active_config_rows INTEGER NOT NULL DEFAULT 0,
    unknown_feature_dependency_rows INTEGER NOT NULL DEFAULT 0,

    recommendation TEXT NOT NULL DEFAULT '',
    source_version TEXT NOT NULL DEFAULT 'STRATEGY_PLATFORM_GOVERNANCE_V1',
    build_id TEXT NOT NULL DEFAULT 'manual',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

GRANT USAGE ON SCHEMA analytics TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA analytics TO alex;
