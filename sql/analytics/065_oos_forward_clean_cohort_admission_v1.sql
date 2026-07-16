BEGIN;

CREATE TABLE IF NOT EXISTS analytics.profit_funnel_oos_forward_admission_decision_v1 (
    decision_id UUID PRIMARY KEY,
    handoff_id UUID NOT NULL UNIQUE REFERENCES analytics.profit_funnel_oos_forward_handoff_v2(handoff_id),
    candidate_uuid UUID NOT NULL UNIQUE,
    decision_code TEXT NOT NULL CHECK (decision_code IN ('PASS','FAIL')),
    reason_code TEXT NOT NULL,
    execution_fingerprint TEXT NOT NULL,
    target_cohort_id UUID,
    evidence JSONB NOT NULL,
    policy_version TEXT NOT NULL,
    evaluator_version TEXT NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK ((decision_code='PASS' AND target_cohort_id IS NOT NULL) OR
           (decision_code='FAIL' AND target_cohort_id IS NULL))
);

REVOKE INSERT, UPDATE, DELETE, TRUNCATE
ON analytics.profit_funnel_oos_forward_admission_decision_v1 FROM PUBLIC;
GRANT SELECT, INSERT ON analytics.profit_funnel_oos_forward_admission_decision_v1 TO alex;

CREATE TRIGGER trg_oos_forward_admission_decision_append_only
BEFORE UPDATE OR DELETE ON analytics.profit_funnel_oos_forward_admission_decision_v1
FOR EACH ROW EXECUTE FUNCTION analytics.prevent_runtime_admission_decision_mutation_v1();

COMMIT;
