BEGIN;
CREATE TABLE IF NOT EXISTS analytics.profit_funnel_runtime_live_admission_v2 (
    admission_id UUID PRIMARY KEY,
    runtime_admission_id UUID NOT NULL UNIQUE,
    runtime_candidate_id UUID NOT NULL UNIQUE,
    live_candidate_id UUID NOT NULL UNIQUE,
    admission_status TEXT NOT NULL CHECK (admission_status IN ('PENDING','ADMITTED','REJECTED','CANCELLED')),
    reason_code TEXT NOT NULL,
    broker_order_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    execution_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    live_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK (NOT broker_order_allowed AND NOT execution_enabled AND NOT live_allowed)
);
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON analytics.profit_funnel_runtime_live_admission_v2 FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE ON analytics.profit_funnel_runtime_live_admission_v2 TO alex;
COMMIT;
