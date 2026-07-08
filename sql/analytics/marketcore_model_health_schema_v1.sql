CREATE TABLE IF NOT EXISTS analytics.marketcore_model_health_snapshot_v1 (
    model_health_snapshot_id BIGSERIAL PRIMARY KEY,

    paper_analytics_snapshot_id BIGINT
        REFERENCES analytics.analytics_snapshot_v1(analytics_snapshot_id)
        ON DELETE SET NULL,

    robustness_snapshot_id BIGINT
        REFERENCES analytics.analytics_snapshot_v1(analytics_snapshot_id)
        ON DELETE SET NULL,

    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.marketcore_model_health_component_v1 (
    component_id BIGSERIAL PRIMARY KEY,

    model_health_snapshot_id BIGINT NOT NULL
        REFERENCES analytics.marketcore_model_health_snapshot_v1(model_health_snapshot_id)
        ON DELETE CASCADE,

    component_code TEXT NOT NULL,
    component_name TEXT NOT NULL,
    component_group TEXT NOT NULL,

    component_value NUMERIC NOT NULL DEFAULT 0,
    component_status TEXT NOT NULL,

    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.marketcore_model_health_gate_v1 (
    gate_id BIGSERIAL PRIMARY KEY,

    model_health_snapshot_id BIGINT NOT NULL
        REFERENCES analytics.marketcore_model_health_snapshot_v1(model_health_snapshot_id)
        ON DELETE CASCADE,

    gate_code TEXT NOT NULL,
    gate_name TEXT NOT NULL,
    gate_status TEXT NOT NULL,
    gate_reason TEXT NOT NULL,

    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.marketcore_model_health_recommendation_v1 (
    model_recommendation_id BIGSERIAL PRIMARY KEY,

    model_health_snapshot_id BIGINT NOT NULL
        REFERENCES analytics.marketcore_model_health_snapshot_v1(model_health_snapshot_id)
        ON DELETE CASCADE,

    recommendation_code TEXT NOT NULL,
    recommendation_scope TEXT NOT NULL,
    recommendation_reason TEXT NOT NULL,
    recommended_action TEXT NOT NULL,

    approved INTEGER NOT NULL DEFAULT 0,
    applied INTEGER NOT NULL DEFAULT 0,
    auto_decision INTEGER NOT NULL DEFAULT 0,

    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_model_health_snapshot_v1
ON analytics.marketcore_model_health_snapshot_v1(created_at DESC, source_version);

CREATE INDEX IF NOT EXISTS idx_model_health_component_snapshot_v1
ON analytics.marketcore_model_health_component_v1(model_health_snapshot_id, component_code);

CREATE INDEX IF NOT EXISTS idx_model_health_gate_snapshot_v1
ON analytics.marketcore_model_health_gate_v1(model_health_snapshot_id, gate_code);

CREATE INDEX IF NOT EXISTS idx_model_health_recommendation_snapshot_v1
ON analytics.marketcore_model_health_recommendation_v1(model_health_snapshot_id, recommendation_scope);
