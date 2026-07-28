CREATE TABLE IF NOT EXISTS analytics.trade_outcome_hypothesis_v1 (
    hypothesis_id UUID PRIMARY KEY,
    hypothesis_key TEXT NOT NULL UNIQUE,
    source_run_id UUID NOT NULL REFERENCES analytics.trade_outcome_pattern_run_v1(run_id),
    hypothesis_type TEXT NOT NULL CHECK (hypothesis_type IN (
        'FILTER_OOS_CANDIDATE','DATA_QUALITY_REMEDIATION',
        'LOSS_FILTER_REMEDIATION','SAMPLE_EXPANSION'
    )),
    strategy_code TEXT NOT NULL,
    side_code TEXT NOT NULL,
    session_code TEXT,
    holding_code TEXT,
    trades INTEGER NOT NULL,
    context_complete_trades INTEGER NOT NULL,
    profit_factor NUMERIC NOT NULL,
    expectancy NUMERIC NOT NULL,
    priority_score NUMERIC NOT NULL,
    lifecycle_state TEXT NOT NULL CHECK (lifecycle_state IN (
        'GENERATED','READY_FOR_OOS','WAITING_CONTEXT','RESTRICTED','CLOSED'
    )),
    recommendation_code TEXT NOT NULL,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS trade_outcome_hypothesis_v1_active_idx
    ON analytics.trade_outcome_hypothesis_v1(lifecycle_state, priority_score DESC, updated_at DESC);

INSERT INTO analytics.system_job_schedule_v1(
    job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
    interval_minutes,timeout_seconds,priority,config_version
) VALUES (
    'TRADE_OUTCOME_HYPOTHESIS_GENERATOR','TRADE_OUTCOME_HYPOTHESIS_GENERATOR_V1',true,
    'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,'00:00','23:59',15,90,28,
    'TRADE_OUTCOME_HYPOTHESIS_GENERATOR_V1'
)
ON CONFLICT(job_code) DO UPDATE SET
    executor_code=excluded.executor_code,enabled=excluded.enabled,
    interval_minutes=excluded.interval_minutes,timeout_seconds=excluded.timeout_seconds,
    priority=excluded.priority,config_version=excluded.config_version,updated_at=clock_timestamp();

GRANT SELECT,INSERT,UPDATE ON analytics.trade_outcome_hypothesis_v1 TO alex;
