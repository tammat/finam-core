BEGIN;

UPDATE analytics.swing_selection_validation_result_v1 SET reason_code=CASE
  WHEN selection_trades<20 THEN 'INSUFFICIENT_SELECTION_TRADES'
  WHEN selection_pf<1.05 OR selection_expectancy<=0 THEN 'SELECTION_EDGE_FAILED'
  WHEN validation_trades<15 THEN 'INSUFFICIENT_VALIDATION_TRADES'
  WHEN validation_pf<1.05 OR validation_expectancy<=0 THEN 'VALIDATION_EDGE_FAILED'
  WHEN validation_folds_passed<2 THEN 'VALIDATION_FOLDS_UNSTABLE'
  WHEN adjusted_p_value>0.05 THEN 'MULTIPLE_TESTING_SIGNIFICANCE_FAILED'
  ELSE reason_code END
WHERE validation_status='VALIDATION_FAIL'
  AND reason_code='SWING_SELECTION_VALIDATION_GATE_FAILED';

CREATE TABLE IF NOT EXISTS analytics.swing_next_research_plan_v1 (
  plan_id uuid PRIMARY KEY,
  source_validation_run_id uuid NOT NULL,
  source_factory_run_id uuid NOT NULL,
  generator_version text NOT NULL,
  status_code text NOT NULL CHECK(status_code IN ('WAITING_FUTURE_DATA','ACTIVE','EVALUATED','EMPTY')),
  item_count integer NOT NULL,
  reason_summary jsonb NOT NULL,
  confirmation_mode text NOT NULL CHECK(confirmation_mode='FUTURE_DATA_ONLY'),
  pass_gates_unchanged boolean NOT NULL CHECK(pass_gates_unchanged),
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE(source_validation_run_id,generator_version)
);

CREATE TABLE IF NOT EXISTS analytics.swing_next_research_plan_item_v1 (
  plan_item_id uuid PRIMARY KEY,
  plan_id uuid NOT NULL REFERENCES analytics.swing_next_research_plan_v1(plan_id),
  priority integer NOT NULL,
  hypothesis_id uuid NOT NULL,
  strategy_family text NOT NULL,
  symbol text NOT NULL,
  timeframe text NOT NULL CHECK(timeframe IN ('H1','H4','D1')),
  source_reason_code text NOT NULL,
  adaptation_code text NOT NULL,
  parameter_snapshot jsonb NOT NULL,
  status_code text NOT NULL CHECK(status_code IN ('WAITING_FUTURE_DATA','ACTIVE','EVALUATED_PASS','EVALUATED_FAIL','REJECTED')),
  rationale_ru text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
  UNIQUE(plan_id,hypothesis_id)
);

INSERT INTO analytics.system_job_schedule_v1
 (job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
  interval_minutes,timeout_seconds,priority,config_version)
VALUES('SWING_NEXT_RESEARCH_PLAN','SWING_NEXT_RESEARCH_PLAN_V1',true,'Europe/Moscow',
 '[0,1,2,3,4,5,6]'::jsonb,time '00:00',time '23:59',60,300,46,'V1')
ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,enabled=true,
 interval_minutes=excluded.interval_minutes,timeout_seconds=excluded.timeout_seconds,
 priority=excluded.priority,config_version=excluded.config_version,updated_at=clock_timestamp();

GRANT SELECT,INSERT,UPDATE ON analytics.swing_next_research_plan_v1,
 analytics.swing_next_research_plan_item_v1 TO alex;

COMMIT;
