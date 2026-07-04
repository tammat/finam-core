CREATE TABLE IF NOT EXISTS analytics.feature_store_health_v1 (
    health_id TEXT PRIMARY KEY DEFAULT 'GLOBAL',
    feature_rows BIGINT NOT NULL DEFAULT 0,
    feature_symbols BIGINT NOT NULL DEFAULT 0,
    latest_bar_ts TIMESTAMPTZ,
    latest_refreshed_at TIMESTAMPTZ,
    max_freshness_sec INTEGER,
    with_return1 BIGINT NOT NULL DEFAULT 0,
    with_volume_ratio20 BIGINT NOT NULL DEFAULT 0,
    timer_active TEXT NOT NULL DEFAULT 'UNKNOWN',
    health_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    diagnosis TEXT NOT NULL DEFAULT '',
    recommended_action TEXT NOT NULL DEFAULT '',
    source_version TEXT NOT NULL DEFAULT 'FEATURE_STORE_HEALTH_V1',
    build_id TEXT NOT NULL DEFAULT 'manual',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

GRANT USAGE ON SCHEMA analytics TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA analytics TO alex;
