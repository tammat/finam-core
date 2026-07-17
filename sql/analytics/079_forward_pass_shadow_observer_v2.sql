BEGIN;

CREATE TABLE IF NOT EXISTS analytics.forward_pass_shadow_policy_v1 (
    policy_code TEXT PRIMARY KEY,
    enabled BOOLEAN NOT NULL,
    source_decision_code TEXT NOT NULL,
    require_review_eligible BOOLEAN NOT NULL,
    future_observations_only BOOLEAN NOT NULL,
    schedule_policy JSONB NOT NULL,
    source_version TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.forward_pass_shadow_policy_v1 VALUES (
 'FORWARD_PASS_SHADOW_V2',TRUE,'READY_FOR_PAPER_REVIEW',TRUE,TRUE,
 '{"timezone":"Europe/Moscow","market_days":[1,2,3,4,5],"hours":"09:00-23:59","interval_minutes":5,"max_parallel_workers":1}'::jsonb,
 'FORWARD_PASS_SHADOW_OBSERVER_V2',clock_timestamp()
) ON CONFLICT(policy_code) DO UPDATE SET
 enabled=TRUE,source_decision_code=EXCLUDED.source_decision_code,
 require_review_eligible=TRUE,future_observations_only=TRUE,
 schedule_policy=EXCLUDED.schedule_policy,source_version=EXCLUDED.source_version,
 updated_at=clock_timestamp();

CREATE TABLE IF NOT EXISTS analytics.forward_pass_shadow_candidate_v1 (
    shadow_candidate_id UUID PRIMARY KEY,
    cohort_id UUID NOT NULL,
    incubator_candidate_id UUID NOT NULL,
    hypothesis_id UUID NOT NULL,
    policy_code TEXT NOT NULL,
    exit_policy_code TEXT NOT NULL,
    strategy_family TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    parameter_json JSONB NOT NULL,
    forward_evidence JSONB NOT NULL,
    execution_fingerprint TEXT NOT NULL UNIQUE,
    observation_not_before TIMESTAMPTZ NOT NULL,
    candidate_status TEXT NOT NULL CHECK(candidate_status IN ('ACTIVE','SUSPENDED')),
    runtime_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    execution_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    live_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    admitted_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    UNIQUE(cohort_id,incubator_candidate_id,exit_policy_code,policy_code)
);

CREATE TABLE IF NOT EXISTS analytics.forward_pass_shadow_observation_v1 (
    shadow_observation_id UUID PRIMARY KEY,
    shadow_candidate_id UUID NOT NULL,
    source_observation_id UUID NOT NULL UNIQUE,
    cohort_id UUID NOT NULL,
    incubator_candidate_id UUID NOT NULL,
    hypothesis_id UUID NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    side TEXT,
    signal_ts TIMESTAMPTZ NOT NULL,
    entry_ts TIMESTAMPTZ,
    exit_ts TIMESTAMPTZ,
    entry_price NUMERIC,
    exit_price NUMERIC,
    qty NUMERIC NOT NULL DEFAULT 1,
    gross_pnl NUMERIC,
    commission NUMERIC,
    spread_cost NUMERIC,
    slippage NUMERIC,
    net_pnl NUMERIC,
    shadow_status TEXT NOT NULL,
    execution_fingerprint TEXT NOT NULL UNIQUE,
    shadow_only BOOLEAN NOT NULL DEFAULT TRUE,
    broker_order_sent BOOLEAN NOT NULL DEFAULT FALSE,
    runtime_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    execution_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS forward_pass_shadow_observation_candidate_idx
ON analytics.forward_pass_shadow_observation_v1(shadow_candidate_id,shadow_status,signal_ts DESC);

CREATE TABLE IF NOT EXISTS analytics.forward_pass_shadow_run_v1 (
    run_id UUID PRIMARY KEY,
    status_code TEXT NOT NULL CHECK(status_code IN ('RUNNING','COMPLETE','SKIPPED','FAILED')),
    reason_code TEXT NOT NULL,
    candidates_admitted INTEGER NOT NULL DEFAULT 0,
    candidates_active INTEGER NOT NULL DEFAULT 0,
    observations_inserted INTEGER NOT NULL DEFAULT 0,
    observations_updated INTEGER NOT NULL DEFAULT 0,
    unsafe_rows INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    finished_at TIMESTAMPTZ,
    source_version TEXT NOT NULL
);

UPDATE analytics.edge_search_scenario_step_v1
SET timeout_seconds=300,required=TRUE
WHERE scenario_code='AUTONOMOUS_EDGE_SEARCH' AND executor_code='PROJECT_SHADOW';

GRANT SELECT ON analytics.forward_pass_shadow_policy_v1 TO alex;
GRANT SELECT,INSERT,UPDATE ON analytics.forward_pass_shadow_candidate_v1 TO alex;
GRANT SELECT,INSERT,UPDATE ON analytics.forward_pass_shadow_observation_v1 TO alex;
GRANT SELECT,INSERT,UPDATE ON analytics.forward_pass_shadow_run_v1 TO alex;
COMMIT;
