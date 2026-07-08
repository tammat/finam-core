CREATE TABLE IF NOT EXISTS analytics.paper_execution_feedback_scope_v1 (
    feedback_scope_code TEXT PRIMARY KEY,
    feedback_scope_name TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.paper_execution_feedback_action_v1 (
    feedback_action_code TEXT PRIMARY KEY,
    feedback_action_name TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS analytics.paper_execution_feedback_v1 (
    feedback_id BIGSERIAL PRIMARY KEY,

    analytics_snapshot_id BIGINT NOT NULL
        REFERENCES analytics.analytics_snapshot_v1(analytics_snapshot_id)
        ON DELETE CASCADE,

    robustness_snapshot_id BIGINT NOT NULL
        REFERENCES analytics.analytics_snapshot_v1(analytics_snapshot_id)
        ON DELETE CASCADE,

    feedback_scope_code TEXT NOT NULL
        REFERENCES analytics.paper_execution_feedback_scope_v1(feedback_scope_code),

    feedback_target TEXT NOT NULL,
    feedback_reason TEXT NOT NULL,
    severity TEXT NOT NULL,
    confidence NUMERIC NOT NULL DEFAULT 0,

    recommended_action_code TEXT NOT NULL
        REFERENCES analytics.paper_execution_feedback_action_v1(feedback_action_code),

    sample_status TEXT NOT NULL,

    approved INTEGER NOT NULL DEFAULT 0,
    applied INTEGER NOT NULL DEFAULT 0,
    auto_decision INTEGER NOT NULL DEFAULT 0,

    evidence_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_version TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_paper_execution_feedback_snapshot_v1
ON analytics.paper_execution_feedback_v1(analytics_snapshot_id, robustness_snapshot_id);

CREATE INDEX IF NOT EXISTS idx_paper_execution_feedback_scope_v1
ON analytics.paper_execution_feedback_v1(feedback_scope_code, recommended_action_code, sample_status);

CREATE INDEX IF NOT EXISTS idx_paper_execution_feedback_approval_v1
ON analytics.paper_execution_feedback_v1(approved, applied, auto_decision);
