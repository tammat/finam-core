BEGIN;

CREATE TABLE IF NOT EXISTS analytics.profit_funnel_transition_lineage_v2 (
    transition_code TEXT PRIMARY KEY,
    from_stage TEXT NOT NULL,
    to_stage TEXT NOT NULL,
    canonical_cohort_id TEXT,
    source_cohort_from TEXT,
    source_cohort_to TEXT,
    from_count BIGINT NOT NULL CHECK (from_count >= 0),
    to_count BIGINT NOT NULL CHECK (to_count >= 0),
    linked_count BIGINT NOT NULL CHECK (linked_count >= 0),
    lineage_status TEXT NOT NULL CHECK (lineage_status IN ('PROVEN','BROKEN','UNVERIFIED')),
    reason_code TEXT NOT NULL,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    observed_at TIMESTAMPTZ NOT NULL,
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK ((lineage_status='PROVEN' AND canonical_cohort_id IS NOT NULL) OR lineage_status<>'PROVEN')
);

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON analytics.profit_funnel_transition_lineage_v2 FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE ON analytics.profit_funnel_transition_lineage_v2 TO alex;

COMMIT;
