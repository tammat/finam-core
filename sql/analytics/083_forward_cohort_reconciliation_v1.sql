CREATE TABLE IF NOT EXISTS analytics.forward_cohort_health_v1 (
    health_key text PRIMARY KEY CHECK (health_key='CURRENT'),
    cohort_id uuid,
    candidate_count integer NOT NULL,
    eligible_candidate_count integer NOT NULL,
    stale_candidate_count integer NOT NULL,
    status_code text NOT NULL,
    reason_code text NOT NULL,
    evidence jsonb NOT NULL,
    source_version text NOT NULL,
    checked_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.system_job_schedule_v1
(job_code,executor_code,enabled,interval_minutes,timezone_code,weekdays,window_start,window_end,priority,timeout_seconds,config_version)
VALUES ('FORWARD_COHORT_RECONCILIATION','FORWARD_COHORT_RECONCILIATION_V1',true,5,'Europe/Moscow',
        '[0,1,2,3,4,5,6]'::jsonb,time '00:00',time '23:59',7,120,'V1_DB_SCHEDULED')
ON CONFLICT(job_code) DO UPDATE SET executor_code=EXCLUDED.executor_code,enabled=true,
 interval_minutes=EXCLUDED.interval_minutes,priority=EXCLUDED.priority,
 timeout_seconds=EXCLUDED.timeout_seconds,config_version=EXCLUDED.config_version,updated_at=clock_timestamp();

GRANT SELECT,INSERT,UPDATE ON analytics.forward_cohort_health_v1 TO alex;
