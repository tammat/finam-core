BEGIN;

CREATE TABLE IF NOT EXISTS analytics.operator_decision_lineage_audit_v2 (
    audit_id BIGSERIAL PRIMARY KEY,
    decision_id UUID NOT NULL,
    lineage_hash TEXT NOT NULL CHECK (lineage_hash ~ '^[0-9a-f]{32}$'),
    transition_code TEXT NOT NULL,
    action_code TEXT NOT NULL,
    source_identity TEXT NOT NULL,
    source_as_of TIMESTAMPTZ NOT NULL,
    evidence JSONB NOT NULL CHECK (evidence <> '{}'::jsonb),
    policy_verdict TEXT NOT NULL,
    autonomy_mode TEXT NOT NULL,
    selection_status TEXT NOT NULL,
    feedback_status TEXT NOT NULL,
    actual_result NUMERIC,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (decision_id, lineage_hash)
);

CREATE INDEX IF NOT EXISTS operator_decision_lineage_audit_transition_time_v2
    ON analytics.operator_decision_lineage_audit_v2 (transition_code, recorded_at DESC);

CREATE OR REPLACE FUNCTION analytics.reject_operator_decision_lineage_audit_mutation_v2()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'OPERATOR_DECISION_LINEAGE_AUDIT_APPEND_ONLY';
END;
$$;

DROP TRIGGER IF EXISTS operator_decision_lineage_audit_append_only_v2
    ON analytics.operator_decision_lineage_audit_v2;
CREATE TRIGGER operator_decision_lineage_audit_append_only_v2
BEFORE UPDATE OR DELETE ON analytics.operator_decision_lineage_audit_v2
FOR EACH ROW EXECUTE FUNCTION analytics.reject_operator_decision_lineage_audit_mutation_v2();

REVOKE UPDATE, DELETE, TRUNCATE ON analytics.operator_decision_lineage_audit_v2 FROM PUBLIC;
GRANT SELECT, INSERT ON analytics.operator_decision_lineage_audit_v2 TO alex;
GRANT USAGE, SELECT ON SEQUENCE analytics.operator_decision_lineage_audit_v2_audit_id_seq TO alex;

COMMIT;
