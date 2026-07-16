BEGIN;

CREATE TABLE IF NOT EXISTS analytics.profit_funnel_runtime_admission_decision_v1 (
    decision_id UUID PRIMARY KEY,
    admission_id UUID NOT NULL,
    decision_code TEXT NOT NULL CHECK (decision_code IN ('PASS','FAIL')),
    policy_version TEXT NOT NULL,
    reason_codes JSONB NOT NULL,
    evidence JSONB NOT NULL,
    evaluator_version TEXT NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (decision_id, admission_id, decision_code),
    FOREIGN KEY (admission_id)
        REFERENCES analytics.profit_funnel_paper_runtime_admission_v2(admission_id)
);

CREATE OR REPLACE FUNCTION analytics.prevent_runtime_admission_decision_mutation_v1()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'RUNTIME_ADMISSION_DECISION_AUDIT_IS_APPEND_ONLY';
END;
$$;

DROP TRIGGER IF EXISTS trg_runtime_admission_decision_append_only
    ON analytics.profit_funnel_runtime_admission_decision_v1;
CREATE TRIGGER trg_runtime_admission_decision_append_only
BEFORE UPDATE OR DELETE ON analytics.profit_funnel_runtime_admission_decision_v1
FOR EACH ROW EXECUTE FUNCTION analytics.prevent_runtime_admission_decision_mutation_v1();

ALTER TABLE analytics.profit_funnel_paper_runtime_admission_v2
    ADD COLUMN IF NOT EXISTS decision_id UUID,
    ADD COLUMN IF NOT EXISTS decision_code TEXT,
    ADD COLUMN IF NOT EXISTS policy_version TEXT,
    ADD COLUMN IF NOT EXISTS decided_at TIMESTAMPTZ;

ALTER TABLE analytics.profit_funnel_paper_runtime_admission_v2
    DROP CONSTRAINT IF EXISTS profit_funnel_paper_runtime_admission_v2_check;

ALTER TABLE analytics.profit_funnel_paper_runtime_admission_v2
    DROP CONSTRAINT IF EXISTS profit_funnel_paper_runtime_admission_v2_decision_check;

ALTER TABLE analytics.profit_funnel_paper_runtime_admission_v2
    ADD CONSTRAINT profit_funnel_paper_runtime_admission_v2_decision_check CHECK (
        NOT execution_enabled
        AND NOT live_allowed
        AND (
            (
                runtime_allowed
                AND admission_status = 'ADMITTED'
                AND decision_code = 'PASS'
                AND decision_id IS NOT NULL
                AND policy_version IS NOT NULL
                AND decided_at IS NOT NULL
            )
            OR
            (
                NOT runtime_allowed
                AND admission_status IN ('PENDING','REJECTED','CANCELLED')
                AND (decision_code IS NULL OR decision_code = 'FAIL')
            )
        )
    );

ALTER TABLE analytics.profit_funnel_paper_runtime_admission_v2
    DROP CONSTRAINT IF EXISTS profit_funnel_paper_runtime_admission_v2_decision_fk;

ALTER TABLE analytics.profit_funnel_paper_runtime_admission_v2
    ADD CONSTRAINT profit_funnel_paper_runtime_admission_v2_decision_fk
    FOREIGN KEY (decision_id, admission_id, decision_code)
    REFERENCES analytics.profit_funnel_runtime_admission_decision_v1 (
        decision_id, admission_id, decision_code
    );

REVOKE UPDATE, DELETE, TRUNCATE
    ON analytics.profit_funnel_runtime_admission_decision_v1 FROM PUBLIC;
GRANT SELECT, INSERT
    ON analytics.profit_funnel_runtime_admission_decision_v1 TO alex;

COMMIT;
