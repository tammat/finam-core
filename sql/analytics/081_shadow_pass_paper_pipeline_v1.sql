BEGIN;

CREATE TABLE IF NOT EXISTS analytics.shadow_pass_policy_v1 (
    policy_code TEXT PRIMARY KEY,
    enabled BOOLEAN NOT NULL,
    minimum_closed INTEGER NOT NULL,
    minimum_calendar_days INTEGER NOT NULL,
    minimum_profit_factor NUMERIC NOT NULL,
    minimum_expectancy NUMERIC NOT NULL,
    maximum_drawdown NUMERIC NOT NULL,
    minimum_cost_coverage NUMERIC NOT NULL,
    minimum_closed_per_regime INTEGER NOT NULL,
    minimum_tested_regimes INTEGER NOT NULL,
    minimum_positive_regime_share NUMERIC NOT NULL,
    config_version TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
INSERT INTO analytics.shadow_pass_policy_v1 VALUES(
 'SHADOW_PASS_V1',TRUE,30,20,1.15,0,1000,0.95,5,2,0.60,'V1_STRICT_COST_ADJUSTED',clock_timestamp()
) ON CONFLICT(policy_code) DO UPDATE SET
 enabled=TRUE,minimum_closed=EXCLUDED.minimum_closed,
 minimum_calendar_days=EXCLUDED.minimum_calendar_days,
 minimum_profit_factor=EXCLUDED.minimum_profit_factor,
 minimum_expectancy=EXCLUDED.minimum_expectancy,
 maximum_drawdown=EXCLUDED.maximum_drawdown,
 minimum_cost_coverage=EXCLUDED.minimum_cost_coverage,
 minimum_closed_per_regime=EXCLUDED.minimum_closed_per_regime,
 minimum_tested_regimes=EXCLUDED.minimum_tested_regimes,
 minimum_positive_regime_share=EXCLUDED.minimum_positive_regime_share,
 config_version=EXCLUDED.config_version,updated_at=clock_timestamp();

CREATE TABLE IF NOT EXISTS analytics.shadow_pass_status_v1 (
    shadow_candidate_id UUID PRIMARY KEY,
    policy_code TEXT NOT NULL,
    decision_code TEXT NOT NULL CHECK(decision_code IN ('PASS','WAIT','FAIL')),
    reason_codes JSONB NOT NULL,
    closed_trades INTEGER NOT NULL,
    calendar_days INTEGER NOT NULL,
    profit_factor NUMERIC,
    expectancy NUMERIC,
    max_drawdown NUMERIC,
    cost_coverage NUMERIC NOT NULL,
    tested_regimes INTEGER NOT NULL,
    positive_regimes INTEGER NOT NULL,
    positive_regime_share NUMERIC NOT NULL,
    progress_pct NUMERIC NOT NULL,
    evidence JSONB NOT NULL,
    policy_version TEXT NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS analytics.shadow_pass_decision_v1 (
    decision_id UUID PRIMARY KEY,
    shadow_candidate_id UUID NOT NULL,
    decision_code TEXT NOT NULL CHECK(decision_code IN ('PASS','WAIT','FAIL')),
    reason_codes JSONB NOT NULL,
    evidence JSONB NOT NULL,
    decision_fingerprint TEXT NOT NULL UNIQUE,
    policy_version TEXT NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS analytics.forward_pass_paper_candidate_v1 (
    paper_candidate_id UUID PRIMARY KEY,
    shadow_candidate_id UUID NOT NULL UNIQUE,
    cohort_id UUID NOT NULL,
    incubator_candidate_id UUID NOT NULL,
    strategy_family TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    parameter_json JSONB NOT NULL,
    shadow_decision_id UUID NOT NULL,
    paper_status TEXT NOT NULL CHECK(paper_status IN ('READY_FOR_PAPER_OBSERVATION','ACTIVE','COMPLETED','REJECTED')),
    paper_allowed BOOLEAN NOT NULL DEFAULT TRUE,
    runtime_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    execution_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    live_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    observation_not_before TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    source_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS analytics.shadow_pipeline_alert_v1 (
    alert_id UUID PRIMARY KEY,
    alert_code TEXT NOT NULL,
    severity_code TEXT NOT NULL CHECK(severity_code IN ('INFO','WARNING','CRITICAL')),
    status_code TEXT NOT NULL CHECK(status_code IN ('OPEN','RESOLVED')),
    reason_code TEXT NOT NULL,
    evidence JSONB NOT NULL,
    alert_fingerprint TEXT NOT NULL UNIQUE,
    opened_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    resolved_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.system_job_schedule_v1
(job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
 interval_minutes,timeout_seconds,priority,config_version,updated_at) VALUES
('SHADOW_PIPELINE_MONITOR','SHADOW_PIPELINE_MONITOR_V1',TRUE,'Europe/Moscow','[0,1,2,3,4]'::jsonb,'09:00','23:59',2,60,5,'V1_DB_SCHEDULED',clock_timestamp()),
('SHADOW_PASS_EVALUATOR','SHADOW_PASS_EVALUATOR_V1',TRUE,'Europe/Moscow','[0,1,2,3,4]'::jsonb,'09:00','23:59',5,120,20,'V1_DB_SCHEDULED',clock_timestamp())
ON CONFLICT(job_code) DO UPDATE SET executor_code=EXCLUDED.executor_code,enabled=TRUE,
 timezone_code=EXCLUDED.timezone_code,weekdays=EXCLUDED.weekdays,
 window_start=EXCLUDED.window_start,window_end=EXCLUDED.window_end,
 interval_minutes=EXCLUDED.interval_minutes,timeout_seconds=EXCLUDED.timeout_seconds,
 priority=EXCLUDED.priority,config_version=EXCLUDED.config_version,updated_at=clock_timestamp();

GRANT SELECT ON analytics.shadow_pass_policy_v1 TO alex;
GRANT SELECT,INSERT,UPDATE ON analytics.shadow_pass_status_v1 TO alex;
GRANT SELECT,INSERT ON analytics.shadow_pass_decision_v1 TO alex;
GRANT SELECT,INSERT,UPDATE ON analytics.forward_pass_paper_candidate_v1 TO alex;
GRANT SELECT,INSERT,UPDATE ON analytics.shadow_pipeline_alert_v1 TO alex;
COMMIT;
