BEGIN;

CREATE TABLE IF NOT EXISTS analytics.research_resource_gate_audit_v1 (
    audit_id BIGSERIAL PRIMARY KEY,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    job_code TEXT NOT NULL,
    executor_code TEXT NOT NULL,
    decision_code TEXT NOT NULL CHECK (decision_code IN ('ALLOW','DEFER')),
    reason_code TEXT NOT NULL,
    load_1m NUMERIC(8,3) NOT NULL,
    load_limit NUMERIC(8,3) NOT NULL
);

CREATE INDEX IF NOT EXISTS research_resource_gate_audit_latest_idx
ON analytics.research_resource_gate_audit_v1(evaluated_at DESC, decision_code);

GRANT SELECT, INSERT ON analytics.research_resource_gate_audit_v1 TO alex;
GRANT USAGE, SELECT ON SEQUENCE analytics.research_resource_gate_audit_v1_audit_id_seq TO alex;

COMMIT;
