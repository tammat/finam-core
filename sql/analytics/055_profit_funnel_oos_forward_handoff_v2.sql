BEGIN;

CREATE TABLE IF NOT EXISTS analytics.profit_funnel_oos_forward_handoff_v2 (
    handoff_id UUID PRIMARY KEY,
    candidate_uuid UUID NOT NULL UNIQUE,
    observation_uuid UUID NOT NULL UNIQUE,
    discovery_batch_id TEXT NOT NULL,
    research_batch_id TEXT NOT NULL,
    oos_result_id BIGINT NOT NULL UNIQUE,
    forward_candidate_id UUID NOT NULL UNIQUE,
    handoff_status TEXT NOT NULL CHECK (handoff_status IN ('PENDING','ADMITTED','REJECTED','CANCELLED')),
    reason_code TEXT NOT NULL,
    target_cohort_id UUID,
    runtime_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    live_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK (NOT runtime_allowed AND NOT live_allowed),
    CHECK ((handoff_status='ADMITTED' AND target_cohort_id IS NOT NULL) OR handoff_status<>'ADMITTED')
);

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON analytics.profit_funnel_oos_forward_handoff_v2 FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE ON analytics.profit_funnel_oos_forward_handoff_v2 TO alex;

COMMIT;
