BEGIN;

CREATE TABLE IF NOT EXISTS analytics.swing_candidate_lifecycle_v1(
 process_id uuid PRIMARY KEY,
 result_id uuid NOT NULL UNIQUE REFERENCES analytics.swing_final_oos_result_v1(result_id),
 plan_item_id uuid NOT NULL REFERENCES analytics.swing_next_research_plan_item_v1(plan_item_id),
 stage_code text NOT NULL CHECK(stage_code IN ('FORWARD','SHADOW','PAPER')),
 status_code text NOT NULL CHECK(status_code IN ('WAITING_DATA','RUNNING','PASS','FAIL','READY')),
 progress_pct integer NOT NULL DEFAULT 0 CHECK(progress_pct BETWEEN 0 AND 100),
 forward_not_before timestamptz NOT NULL,
 shadow_cohort_id uuid,
 paper_allowed boolean NOT NULL DEFAULT false,
 live_allowed boolean NOT NULL DEFAULT false,
 gate_evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
 reason_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
 heartbeat_at timestamptz,
 last_error text,
 created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS analytics.swing_paper_admission_v1(
 admission_id uuid PRIMARY KEY,
 process_id uuid NOT NULL UNIQUE REFERENCES analytics.swing_candidate_lifecycle_v1(process_id),
 shadow_cohort_id uuid NOT NULL,
 admitted_at timestamptz NOT NULL DEFAULT clock_timestamp(),
 admission_evidence jsonb NOT NULL,
 paper_allowed boolean NOT NULL CHECK(paper_allowed),
 live_allowed boolean NOT NULL DEFAULT false CHECK(NOT live_allowed)
);

INSERT INTO analytics.system_job_schedule_v1
 (job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
 interval_minutes,timeout_seconds,priority,config_version)
VALUES
 ('SWING_AUTONOMOUS_LIFECYCLE','SWING_AUTONOMOUS_LIFECYCLE_V1',true,'Europe/Moscow',
  '[0,1,2,3,4,5,6]'::jsonb,time '00:00',time '23:59',60,600,49,'V1'),
 ('SWING_SHADOW_OBSERVER','SWING_SHADOW_OBSERVER_V1',true,'Europe/Moscow',
  '[0,1,2,3,4,5,6]'::jsonb,time '00:00',time '23:59',60,600,50,'V1')
ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,enabled=true,
 interval_minutes=excluded.interval_minutes,timeout_seconds=excluded.timeout_seconds,
 priority=excluded.priority,config_version=excluded.config_version,updated_at=clock_timestamp();

GRANT SELECT,INSERT,UPDATE ON analytics.swing_candidate_lifecycle_v1,
 analytics.swing_paper_admission_v1 TO alex;
COMMIT;
