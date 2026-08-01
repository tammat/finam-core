BEGIN;

CREATE TABLE IF NOT EXISTS analytics.lightweight_statistical_run_v1(
 run_id uuid PRIMARY KEY,status_code text NOT NULL CHECK(status_code IN('RUNNING','COMPLETE','FAILED')),
 groups_total integer NOT NULL DEFAULT 0,ready_for_expensive_gates integer NOT NULL DEFAULT 0,
 degradation_alerts integer NOT NULL DEFAULT 0,started_at timestamptz NOT NULL DEFAULT clock_timestamp(),finished_at timestamptz);

CREATE TABLE IF NOT EXISTS analytics.lightweight_statistical_evidence_v1(
 run_id uuid NOT NULL REFERENCES analytics.lightweight_statistical_run_v1(run_id) ON DELETE CASCADE,
 symbol text NOT NULL,side_code text NOT NULL,strategy_code text NOT NULL,regime_code text NOT NULL,
 trades integer NOT NULL,net_pnl numeric NOT NULL,expectancy numeric NOT NULL,
 bootstrap_ci_low numeric NOT NULL,bootstrap_ci_high numeric NOT NULL,probability_positive numeric NOT NULL,
 block_length integer NOT NULL,mde_required_trades integer,mde_remaining_trades integer,
 top_trade_profit_share numeric NOT NULL,top_day_profit_share numeric NOT NULL,
 leave_one_out_min_expectancy numeric NOT NULL,median_hold_seconds integer NOT NULL,
 survival_summary jsonb NOT NULL,cusum_status text NOT NULL,cusum_score numeric NOT NULL,
 verdict_code text NOT NULL,reason_code text NOT NULL,created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 PRIMARY KEY(run_id,symbol,side_code,strategy_code,regime_code));
CREATE INDEX IF NOT EXISTS lightweight_statistical_evidence_latest_idx
 ON analytics.lightweight_statistical_evidence_v1(created_at DESC,verdict_code,cusum_status);

INSERT INTO analytics.system_job_schedule_v1(job_code,executor_code,enabled,timezone_code,weekdays,
 window_start,window_end,interval_minutes,timeout_seconds,priority,config_version)
VALUES('LIGHTWEIGHT_STATISTICAL_EVIDENCE_NIGHT','LIGHTWEIGHT_STATISTICAL_EVIDENCE_V1',true,
 'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,time '21:20',time '23:30',1440,900,33,'V1_RESOURCE_GATED')
ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,enabled=true,
 timezone_code=excluded.timezone_code,weekdays=excluded.weekdays,window_start=excluded.window_start,
 window_end=excluded.window_end,interval_minutes=excluded.interval_minutes,
 timeout_seconds=excluded.timeout_seconds,priority=excluded.priority,
 config_version=excluded.config_version,updated_at=clock_timestamp();

GRANT SELECT,INSERT,UPDATE ON analytics.lightweight_statistical_run_v1,
 analytics.lightweight_statistical_evidence_v1 TO alex;

COMMIT;
