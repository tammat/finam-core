CREATE TABLE IF NOT EXISTS analytics.paper_execution_robustness_audit_v1 (
    robustness_audit_id BIGSERIAL PRIMARY KEY,
    analytics_snapshot_id BIGINT NOT NULL
        REFERENCES analytics.analytics_snapshot_v1(analytics_snapshot_id)
        ON DELETE CASCADE,

    paper_analytics_snapshot_id BIGINT NOT NULL
        REFERENCES analytics.analytics_snapshot_v1(analytics_snapshot_id)
        ON DELETE CASCADE,

    sample_trades INTEGER NOT NULL DEFAULT 0,
    time_bucket_count INTEGER NOT NULL DEFAULT 0,
    instrument_count INTEGER NOT NULL DEFAULT 0,
    regime_count INTEGER NOT NULL DEFAULT 0,
    source_count INTEGER NOT NULL DEFAULT 0,

    sample_score NUMERIC NOT NULL DEFAULT 0,
    time_stability_score NUMERIC NOT NULL DEFAULT 0,
    instrument_stability_score NUMERIC NOT NULL DEFAULT 0,
    regime_stability_score NUMERIC NOT NULL DEFAULT 0,
    source_stability_score NUMERIC NOT NULL DEFAULT 0,

    robustness_score NUMERIC NOT NULL DEFAULT 0,
    learning_readiness_index NUMERIC NOT NULL DEFAULT 0,

    sample_status TEXT NOT NULL,
    overfit_risk TEXT NOT NULL,
    production_allowed INTEGER NOT NULL DEFAULT 0,
    auto_decision INTEGER NOT NULL DEFAULT 0,

    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_paper_execution_robustness_audit_snapshot_v1
ON analytics.paper_execution_robustness_audit_v1(analytics_snapshot_id);
