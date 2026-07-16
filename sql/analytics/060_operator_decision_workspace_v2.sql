BEGIN;

CREATE TABLE IF NOT EXISTS analytics.operator_action_policy_v2 (
    reason_code TEXT PRIMARY KEY,
    action_code TEXT NOT NULL UNIQUE,
    priority INTEGER NOT NULL CHECK (priority > 0),
    policy_verdict TEXT NOT NULL CHECK (policy_verdict IN ('REVIEW_REQUIRED','BLOCKED')),
    autonomy_mode TEXT NOT NULL CHECK (autonomy_mode IN ('OBSERVE_ONLY','OPERATOR_APPROVAL')),
    validity_seconds INTEGER NOT NULL CHECK (validity_seconds > 0),
    risk_impact_code TEXT NOT NULL,
    rollback_plan_code TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE
);

INSERT INTO analytics.operator_action_policy_v2 VALUES
('NO_SHADOW_CANDIDATE_ELIGIBLE','REVIEW_SHADOW_LOSS',10,'REVIEW_REQUIRED','OPERATOR_APPROVAL',3600,'REDUCE_LOSS_EXPOSURE','KEEP_PAPER_ADMISSION_BLOCKED',true),
('HANDOFF_PENDING_FORWARD_ADMISSION','REVIEW_FORWARD_ADMISSION',20,'REVIEW_REQUIRED','OPERATOR_APPROVAL',3600,'NO_RISK_EXPANSION','CANCEL_FORWARD_HANDOFF',true),
('RUNTIME_ADMISSION_PENDING','RESTORE_RUNTIME_EVIDENCE',30,'REVIEW_REQUIRED','OPERATOR_APPROVAL',3600,'NO_RISK_EXPANSION','CANCEL_RUNTIME_HANDOFF',true),
('NO_RUNTIME_CANDIDATE_ADMITTED','KEEP_LIVE_BLOCKED',40,'BLOCKED','OBSERVE_ONLY',3600,'PREVENT_UNVERIFIED_LIVE','KEEP_LIVE_DISABLED',true),
('NO_REAL_EXECUTION','OBSERVE_REAL_EXECUTION_BOUNDARY',50,'BLOCKED','OBSERVE_ONLY',3600,'PREVENT_UNAUTHORIZED_EXECUTION','KEEP_LIVE_DISABLED',true)
ON CONFLICT (reason_code) DO UPDATE SET
    action_code=EXCLUDED.action_code,priority=EXCLUDED.priority,
    policy_verdict=EXCLUDED.policy_verdict,autonomy_mode=EXCLUDED.autonomy_mode,
    validity_seconds=EXCLUDED.validity_seconds,risk_impact_code=EXCLUDED.risk_impact_code,
    rollback_plan_code=EXCLUDED.rollback_plan_code,enabled=EXCLUDED.enabled;

CREATE TABLE IF NOT EXISTS analytics.operator_decision_workspace_v2 (
    decision_id UUID PRIMARY KEY,
    rank INTEGER NOT NULL CHECK (rank > 0),
    transition_code TEXT NOT NULL UNIQUE,
    bottleneck_stage TEXT NOT NULL,
    loss_source_code TEXT NOT NULL,
    action_code TEXT NOT NULL,
    evidence JSONB NOT NULL,
    source_identity TEXT NOT NULL,
    source_as_of TIMESTAMPTZ NOT NULL,
    freshness_code TEXT NOT NULL CHECK (freshness_code IN ('CURRENT','STALE')),
    expected_profit_impact NUMERIC,
    risk_impact_code TEXT NOT NULL,
    confidence NUMERIC NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    sample_size BIGINT NOT NULL CHECK (sample_size >= 0),
    sample_sufficiency_code TEXT NOT NULL CHECK (sample_sufficiency_code IN ('SUFFICIENT','INSUFFICIENT','NOT_APPLICABLE')),
    policy_verdict TEXT NOT NULL CHECK (policy_verdict IN ('REVIEW_REQUIRED','BLOCKED')),
    autonomy_mode TEXT NOT NULL CHECK (autonomy_mode IN ('OBSERVE_ONLY','OPERATOR_APPROVAL')),
    expires_at TIMESTAMPTZ NOT NULL,
    rollback_plan_code TEXT NOT NULL,
    actual_result NUMERIC,
    feedback_status TEXT NOT NULL CHECK (feedback_status IN ('PENDING','MEASURED','NOT_APPLICABLE')),
    quality_code TEXT NOT NULL CHECK (quality_code='UNVERIFIED'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON analytics.operator_action_policy_v2 FROM PUBLIC;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON analytics.operator_decision_workspace_v2 FROM PUBLIC;
GRANT SELECT ON analytics.operator_action_policy_v2 TO alex;
GRANT SELECT, INSERT, UPDATE ON analytics.operator_decision_workspace_v2 TO alex;

COMMIT;
