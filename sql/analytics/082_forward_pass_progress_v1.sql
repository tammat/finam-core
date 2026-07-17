CREATE TABLE IF NOT EXISTS analytics.forward_pass_readiness_v1 (
    cohort_id uuid NOT NULL,
    incubator_candidate_id uuid NOT NULL,
    policy_code text NOT NULL,
    closed_observations integer NOT NULL,
    calendar_days integer NOT NULL,
    attribution_coverage numeric NOT NULL,
    tested_regimes integer NOT NULL,
    positive_regime_share numeric NOT NULL,
    variant_net_pnl numeric NOT NULL,
    evidence_progress_pct numeric NOT NULL CHECK (evidence_progress_pct BETWEEN 0 AND 100),
    regime_progress_pct numeric NOT NULL CHECK (regime_progress_pct BETWEEN 0 AND 100),
    overall_progress_pct numeric NOT NULL CHECK (overall_progress_pct BETWEEN 0 AND 100),
    readiness_rank integer NOT NULL,
    decision_code text NOT NULL,
    reason_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
    source_updated_at timestamptz,
    refreshed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (cohort_id, incubator_candidate_id, policy_code)
);

CREATE TABLE IF NOT EXISTS analytics.forward_remediation_scenario_v1 (
    scenario_id uuid PRIMARY KEY,
    cohort_id uuid NOT NULL,
    incubator_candidate_id uuid NOT NULL,
    policy_code text NOT NULL,
    scenario_code text NOT NULL,
    reason_codes jsonb NOT NULL,
    action_policy jsonb NOT NULL,
    selection_cutoff_ts timestamptz NOT NULL,
    observation_not_before timestamptz NOT NULL,
    selection_uses_final_holdout boolean NOT NULL DEFAULT false CHECK (NOT selection_uses_final_holdout),
    status_code text NOT NULL,
    source_version text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (cohort_id, incubator_candidate_id, policy_code, scenario_code, source_version)
);

CREATE TABLE IF NOT EXISTS analytics.forward_pass_stage_status_v1 (
    step_order smallint PRIMARY KEY CHECK (step_order BETWEEN 1 AND 6),
    step_code text NOT NULL UNIQUE,
    status_code text NOT NULL,
    progress_pct numeric NOT NULL CHECK (progress_pct BETWEEN 0 AND 100),
    item_count integer NOT NULL DEFAULT 0,
    reason_code text NOT NULL,
    evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
    source_as_of timestamptz,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.system_job_schedule_v1
    (job_code,executor_code,enabled,interval_minutes,timezone_code,weekdays,window_start,window_end,priority,timeout_seconds,config_version)
VALUES
    ('FORWARD_EVIDENCE_PIPELINE','FORWARD_EVIDENCE_PIPELINE_V1',true,15,'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,time '00:00',time '23:59',8,1200,'V1_DB_SCHEDULED'),
    ('FORWARD_PASS_PROGRESS','FORWARD_PASS_PROGRESS_V1',true,15,'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,time '00:00',time '23:59',15,120,'V1_DB_SCHEDULED'),
    ('FORWARD_REMEDIATION_SCENARIOS','FORWARD_REMEDIATION_SCENARIOS_V1',true,5,'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,time '00:00',time '23:59',30,120,'V1_DB_SCHEDULED')
ON CONFLICT (job_code) DO UPDATE SET
    executor_code=EXCLUDED.executor_code, enabled=EXCLUDED.enabled,
    interval_minutes=EXCLUDED.interval_minutes, priority=EXCLUDED.priority,
    timeout_seconds=EXCLUDED.timeout_seconds;
