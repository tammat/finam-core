CREATE TABLE IF NOT EXISTS analytics.trade_outcome_pattern_run_v1 (
    run_id UUID PRIMARY KEY,
    source_max_closed_at TIMESTAMPTZ,
    total_trades INTEGER NOT NULL,
    profitable_trades INTEGER NOT NULL,
    loss_trades INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS analytics.trade_outcome_pattern_result_v1 (
    run_id UUID NOT NULL REFERENCES analytics.trade_outcome_pattern_run_v1(run_id) ON DELETE CASCADE,
    dimension_code TEXT NOT NULL,
    dimension_value TEXT NOT NULL,
    trades INTEGER NOT NULL,
    winners INTEGER NOT NULL,
    losers INTEGER NOT NULL,
    win_rate NUMERIC NOT NULL,
    gross_profit NUMERIC NOT NULL,
    gross_loss NUMERIC NOT NULL,
    profit_factor NUMERIC NOT NULL,
    expectancy NUMERIC NOT NULL,
    outcome_code TEXT NOT NULL CHECK(outcome_code IN ('PROFITABLE','LOSS_MAKING','INSUFFICIENT_SAMPLE')),
    recommendation_code TEXT NOT NULL,
    PRIMARY KEY(run_id,dimension_code,dimension_value)
);
CREATE INDEX IF NOT EXISTS trade_outcome_pattern_result_v1_rank_idx
    ON analytics.trade_outcome_pattern_result_v1(run_id, outcome_code, expectancy DESC);

INSERT INTO analytics.system_job_schedule_v1(
    job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
    interval_minutes,timeout_seconds,priority,config_version
) VALUES (
    'TRADE_OUTCOME_PATTERN_ANALYSIS','TRADE_OUTCOME_PATTERN_ANALYSIS_V1',true,'Europe/Moscow',
    '[0,1,2,3,4,5,6]'::jsonb,'00:00','23:59',5,90,25,'TRADE_OUTCOME_PATTERN_ANALYSIS_V1'
)
ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,enabled=excluded.enabled,
 interval_minutes=excluded.interval_minutes,timeout_seconds=excluded.timeout_seconds,priority=excluded.priority,
 config_version=excluded.config_version,updated_at=clock_timestamp();

GRANT SELECT,INSERT ON analytics.trade_outcome_pattern_run_v1,analytics.trade_outcome_pattern_result_v1 TO alex;
