BEGIN;

ALTER TABLE analytics.swing_next_research_plan_v1
 ADD COLUMN IF NOT EXISTS heartbeat_at timestamptz,
 ADD COLUMN IF NOT EXISTS last_error_code text,
 ADD COLUMN IF NOT EXISTS attempt_count integer NOT NULL DEFAULT 0;
ALTER TABLE analytics.swing_next_research_plan_item_v1
 ADD COLUMN IF NOT EXISTS confirmation_after_ts timestamptz,
 ADD COLUMN IF NOT EXISTS minimum_future_bars integer,
 ADD COLUMN IF NOT EXISTS activated_at timestamptz,
 ADD COLUMN IF NOT EXISTS evaluated_at timestamptz;

UPDATE analytics.swing_next_research_plan_item_v1 i SET
 confirmation_after_ts=coalesce(confirmation_after_ts,(SELECT max(ts) FROM analytics.swing_market_bars_v1 b WHERE b.symbol=i.symbol AND b.timeframe=i.timeframe),i.created_at),
 minimum_future_bars=coalesce(minimum_future_bars,CASE timeframe WHEN 'H1' THEN 120 WHEN 'H4' THEN 40 ELSE 20 END)
WHERE confirmation_after_ts IS NULL OR minimum_future_bars IS NULL;
ALTER TABLE analytics.swing_next_research_plan_item_v1 ALTER COLUMN confirmation_after_ts SET NOT NULL;
ALTER TABLE analytics.swing_next_research_plan_item_v1 ALTER COLUMN minimum_future_bars SET NOT NULL;

CREATE TABLE IF NOT EXISTS analytics.swing_final_oos_result_v1(
 result_id uuid PRIMARY KEY,plan_item_id uuid NOT NULL UNIQUE REFERENCES analytics.swing_next_research_plan_item_v1(plan_item_id),
 holdout_fingerprint text NOT NULL UNIQUE,holdout_start timestamptz NOT NULL,holdout_end timestamptz NOT NULL,
 trades integer NOT NULL,profit_factor numeric NOT NULL,expectancy numeric NOT NULL,folds_passed integer NOT NULL,
 adjusted_p_value numeric NOT NULL,stressed_expectancy numeric NOT NULL,capacity_rub numeric NOT NULL,
 portfolio_correlation numeric,statistical_pass boolean NOT NULL,robustness_pass boolean NOT NULL,
 holdout_pass boolean NOT NULL,execution_pass boolean NOT NULL,capacity_pass boolean NOT NULL,
 portfolio_pass boolean NOT NULL,verdict_code text NOT NULL,promotion_allowed boolean NOT NULL DEFAULT false,
 reason_codes jsonb NOT NULL,execution_policy jsonb NOT NULL,created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.system_job_schedule_v1(job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,interval_minutes,timeout_seconds,priority,config_version)
VALUES
 ('SWING_FUTURE_EXECUTION','SWING_FUTURE_EXECUTION_V1',true,'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,time '00:00',time '23:59',60,900,47,'V1'),
 ('SWING_PROCESS_MONITOR','SWING_PROCESS_MONITOR_V1',true,'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,time '00:00',time '23:59',10,60,48,'V1')
ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,enabled=true,interval_minutes=excluded.interval_minutes,
 timeout_seconds=excluded.timeout_seconds,priority=excluded.priority,config_version=excluded.config_version,updated_at=clock_timestamp();
GRANT SELECT,INSERT,UPDATE ON analytics.swing_final_oos_result_v1 TO alex;
COMMIT;
