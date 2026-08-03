BEGIN;

CREATE TABLE IF NOT EXISTS analytics.v5_frozen_causal_replay_v1 (
    replay_run_id uuid NOT NULL,
    branch_code text NOT NULL,
    candidate_code text NOT NULL,
    observation_symbol text NOT NULL,
    side_code text NOT NULL,
    window_start timestamptz NOT NULL,
    window_end timestamptz NOT NULL,
    source_signals integer NOT NULL,
    entered_signals integer NOT NULL,
    completed_outcomes integer NOT NULL,
    entry_rate numeric NOT NULL,
    net_r numeric,
    expectancy_r numeric,
    paired_placebo_r numeric,
    edge_over_placebo_r numeric,
    diagnostic_verdict text NOT NULL,
    reason_code text NOT NULL,
    gate_mode text NOT NULL DEFAULT 'DIAGNOSTIC_ONLY',
    source_version text NOT NULL DEFAULT 'V5_FROZEN_CAUSAL_REPLAY_V1',
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY(replay_run_id, branch_code),
    CHECK(gate_mode='DIAGNOSTIC_ONLY')
);

GRANT SELECT,INSERT ON analytics.v5_frozen_causal_replay_v1 TO alex,finam;

COMMIT;
