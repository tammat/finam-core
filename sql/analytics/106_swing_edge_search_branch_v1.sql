BEGIN;

CREATE TABLE IF NOT EXISTS analytics.swing_edge_search_run_v1 (
    run_id uuid PRIMARY KEY,
    scenario_code text NOT NULL CHECK(scenario_code='SWING_EDGE_SEARCH'),
    source_plan_id uuid NOT NULL REFERENCES analytics.edge_next_research_plan_v1(plan_id),
    source_failure_reasons jsonb NOT NULL CHECK(jsonb_typeof(source_failure_reasons)='array'),
    status_code text NOT NULL CHECK(status_code IN ('RUNNING','SUCCEEDED','NO_PASS','FAILED','SKIPPED')),
    current_step text NOT NULL,
    progress_pct integer NOT NULL CHECK(progress_pct BETWEEN 0 AND 100),
    validation_pass integer NOT NULL DEFAULT 0,
    reason_code text,
    config_version text NOT NULL,
    started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    finished_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE(source_plan_id,config_version)
);

CREATE TABLE IF NOT EXISTS analytics.swing_edge_search_step_run_v1 (
    step_run_id uuid PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES analytics.swing_edge_search_run_v1(run_id),
    step_order integer NOT NULL,
    step_code text NOT NULL,
    status_code text NOT NULL CHECK(status_code IN ('RUNNING','SUCCEEDED','FAILED','SKIPPED')),
    started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    finished_at timestamptz,
    duration_ms bigint,
    return_code integer,
    stdout_tail text,
    stderr_tail text,
    UNIQUE(run_id,step_order)
);

INSERT INTO analytics.edge_search_scenario_v1
  (scenario_code,title_ru,enabled,schedule_policy,result_policy,config_version)
VALUES('SWING_EDGE_SEARCH','Поиск среднесрочного преимущества',true,
  '{"owner":"system","trigger":"db_scheduler","manual_algorithm_start":false,"timeframes":["H1","H4","D1"]}'::jsonb,
  '{"source":"methodology_failures","persist_steps":true,"pass_gates":"unchanged","live_allowed":false}'::jsonb,
  'V1_FAIL_DRIVEN')
ON CONFLICT(scenario_code) DO UPDATE SET title_ru=excluded.title_ru,enabled=true,
 schedule_policy=excluded.schedule_policy,result_policy=excluded.result_policy,
 config_version=excluded.config_version,updated_at=clock_timestamp();

INSERT INTO analytics.system_job_schedule_v1
 (job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
  interval_minutes,timeout_seconds,priority,config_version)
VALUES
 ('SWING_EDGE_SEARCH_NIGHT','SWING_EDGE_SEARCH_CYCLE_V1',true,'Europe/Moscow','[0,1,2,3,4]'::jsonb,
  time '00:00',time '08:59',360,3600,45,'V1_FAIL_DRIVEN'),
 ('SWING_EDGE_SEARCH_WEEKEND','SWING_EDGE_SEARCH_CYCLE_V1',true,'Europe/Moscow','[5,6]'::jsonb,
  time '00:00',time '23:59',360,3600,45,'V1_FAIL_DRIVEN')
ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,enabled=true,
 timezone_code=excluded.timezone_code,weekdays=excluded.weekdays,window_start=excluded.window_start,
 window_end=excluded.window_end,interval_minutes=excluded.interval_minutes,
 timeout_seconds=excluded.timeout_seconds,priority=excluded.priority,
 config_version=excluded.config_version,updated_at=clock_timestamp();

GRANT SELECT,INSERT,UPDATE ON analytics.swing_edge_search_run_v1,
 analytics.swing_edge_search_step_run_v1 TO alex;

COMMIT;
