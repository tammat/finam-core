BEGIN;

CREATE SCHEMA IF NOT EXISTS marketcore_action;

CREATE TABLE IF NOT EXISTS marketcore_action.action_audit_v2 (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    occurred_at TIMESTAMPTZ NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    stage TEXT NOT NULL CHECK (stage IN ('DECISION','EXECUTION_STARTED','EXECUTION_FINISHED')),
    action_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    interaction_kind TEXT NOT NULL CHECK (interaction_kind IN ('CLICK','DOUBLE_CLICK')),
    status TEXT NOT NULL CHECK (status IN ('NAVIGATED','EXECUTED','DENIED','APPROVAL_REQUIRED','DUPLICATE','FAILED')),
    reason_code TEXT NOT NULL,
    target_id TEXT,
    command_code TEXT,
    policy_class TEXT,
    risk_guard_code TEXT,
    idempotency_key TEXT,
    approval_granted BOOLEAN NOT NULL DEFAULT FALSE,
    result_reference TEXT
);

CREATE INDEX IF NOT EXISTS action_audit_v2_action_time_idx
    ON marketcore_action.action_audit_v2 (action_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS action_audit_v2_actor_time_idx
    ON marketcore_action.action_audit_v2 (actor_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS action_audit_v2_idempotency_idx
    ON marketcore_action.action_audit_v2 (idempotency_key)
    WHERE idempotency_key IS NOT NULL;

CREATE OR REPLACE FUNCTION marketcore_action.reject_action_audit_mutation_v2()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'ACTION_AUDIT_V2_APPEND_ONLY';
END;
$$;

DROP TRIGGER IF EXISTS action_audit_v2_append_only ON marketcore_action.action_audit_v2;
CREATE TRIGGER action_audit_v2_append_only
BEFORE UPDATE OR DELETE ON marketcore_action.action_audit_v2
FOR EACH ROW EXECUTE FUNCTION marketcore_action.reject_action_audit_mutation_v2();

REVOKE UPDATE, DELETE, TRUNCATE ON marketcore_action.action_audit_v2 FROM PUBLIC;

CREATE TABLE IF NOT EXISTS marketcore_action.idempotency_claim_v2 (
    idempotency_key TEXT PRIMARY KEY,
    claimed_at TIMESTAMPTZ NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

REVOKE UPDATE ON marketcore_action.idempotency_claim_v2 FROM PUBLIC;

COMMIT;
