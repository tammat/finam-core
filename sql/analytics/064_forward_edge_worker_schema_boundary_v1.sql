BEGIN;

ALTER TABLE analytics.forward_edge_observation_v1
    ADD COLUMN IF NOT EXISTS side TEXT,
    ADD COLUMN IF NOT EXISTS holding_bars INTEGER,
    ADD COLUMN IF NOT EXISTS entry_price NUMERIC,
    ADD COLUMN IF NOT EXISTS exit_price NUMERIC,
    ADD COLUMN IF NOT EXISTS planned_entry_ts TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS signal_context JSONB;

CREATE TABLE IF NOT EXISTS analytics.forward_edge_worker_state_v1 (
    cohort_id UUID NOT NULL,
    incubator_candidate_id UUID NOT NULL,
    last_evaluated_ts TIMESTAMPTZ,
    worker_status TEXT NOT NULL,
    last_error TEXT,
    source_version TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (cohort_id, incubator_candidate_id)
);

GRANT SELECT, INSERT, UPDATE ON analytics.forward_edge_worker_state_v1 TO alex;

COMMIT;
