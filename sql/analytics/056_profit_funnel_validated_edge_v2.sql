BEGIN;
CREATE TABLE IF NOT EXISTS analytics.profit_funnel_validated_edge_v2 (
    validation_id UUID PRIMARY KEY,
    candidate_uuid UUID NOT NULL UNIQUE,
    observation_uuid UUID NOT NULL UNIQUE,
    discovery_batch_id TEXT NOT NULL,
    validation_score NUMERIC NOT NULL,
    validation_formula_version TEXT NOT NULL,
    validation_status TEXT NOT NULL CHECK (validation_status='PASS'),
    paper_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    runtime_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    live_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    source_version TEXT NOT NULL,
    validated_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK (NOT paper_allowed AND NOT runtime_allowed AND NOT live_allowed)
);
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON analytics.profit_funnel_validated_edge_v2 FROM PUBLIC;
GRANT SELECT, INSERT ON analytics.profit_funnel_validated_edge_v2 TO alex;
COMMIT;
