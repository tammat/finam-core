BEGIN;
CREATE TABLE IF NOT EXISTS analytics.profit_funnel_paper_runtime_admission_v2 (
    admission_id UUID PRIMARY KEY,
    paper_candidate_id BIGINT NOT NULL UNIQUE,
    observation_uuid UUID NOT NULL UNIQUE,
    runtime_candidate_id UUID NOT NULL UNIQUE,
    admission_status TEXT NOT NULL CHECK (admission_status IN ('PENDING','ADMITTED','REJECTED','CANCELLED')),
    reason_code TEXT NOT NULL,
    runtime_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    execution_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    live_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK (NOT runtime_allowed AND NOT execution_enabled AND NOT live_allowed)
);
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON analytics.profit_funnel_paper_runtime_admission_v2 FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE ON analytics.profit_funnel_paper_runtime_admission_v2 TO alex;
COMMIT;
