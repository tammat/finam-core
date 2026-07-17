BEGIN;

CREATE TABLE IF NOT EXISTS analytics.forward_pass_shadow_heartbeat_v1 (
    worker_code TEXT PRIMARY KEY,
    status_code TEXT NOT NULL CHECK(status_code IN ('NEVER_RUN','RUNNING','HEALTHY','FAILED')),
    last_started_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    last_failure_at TIMESTAMPTZ,
    current_run_id UUID,
    candidates_active INTEGER NOT NULL DEFAULT 0,
    observations_inserted INTEGER NOT NULL DEFAULT 0,
    observations_updated INTEGER NOT NULL DEFAULT 0,
    unsafe_rows INTEGER NOT NULL DEFAULT 0,
    last_error_code TEXT,
    last_error_detail TEXT,
    source_version TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
INSERT INTO analytics.forward_pass_shadow_heartbeat_v1(worker_code,status_code,source_version)
VALUES('FORWARD_PASS_SHADOW_OBSERVER','NEVER_RUN','FORWARD_PASS_SHADOW_OBSERVER_V2')
ON CONFLICT(worker_code) DO NOTHING;

CREATE TABLE IF NOT EXISTS analytics.system_job_schedule_v1 (
    job_code TEXT PRIMARY KEY,
    executor_code TEXT NOT NULL,
    enabled BOOLEAN NOT NULL,
    timezone_code TEXT NOT NULL,
    weekdays JSONB NOT NULL CHECK(jsonb_typeof(weekdays)='array'),
    window_start TIME NOT NULL,
    window_end TIME NOT NULL,
    interval_minutes INTEGER NOT NULL CHECK(interval_minutes BETWEEN 1 AND 1440),
    timeout_seconds INTEGER NOT NULL CHECK(timeout_seconds BETWEEN 1 AND 3600),
    priority INTEGER NOT NULL DEFAULT 100,
    config_version TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);
INSERT INTO analytics.system_job_schedule_v1 VALUES(
 'FORWARD_PASS_SHADOW_OBSERVER','FORWARD_PASS_SHADOW_OBSERVER_V2',TRUE,'Europe/Moscow',
 '[0,1,2,3,4]'::jsonb,'09:00','23:59',5,240,10,'V1_DB_SCHEDULED',clock_timestamp()
) ON CONFLICT(job_code) DO UPDATE SET
 executor_code=EXCLUDED.executor_code,enabled=TRUE,timezone_code=EXCLUDED.timezone_code,
 weekdays=EXCLUDED.weekdays,window_start=EXCLUDED.window_start,window_end=EXCLUDED.window_end,
 interval_minutes=EXCLUDED.interval_minutes,timeout_seconds=EXCLUDED.timeout_seconds,
 priority=EXCLUDED.priority,config_version=EXCLUDED.config_version,updated_at=clock_timestamp();

CREATE TABLE IF NOT EXISTS analytics.system_job_run_v1 (
    scheduler_run_id UUID PRIMARY KEY,
    job_code TEXT NOT NULL,
    executor_code TEXT NOT NULL,
    status_code TEXT NOT NULL CHECK(status_code IN ('RUNNING','COMPLETE','FAILED','TIMEOUT')),
    return_code INTEGER,
    stdout_tail TEXT,
    stderr_tail TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    finished_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS system_job_run_latest_idx
ON analytics.system_job_run_v1(job_code,started_at DESC);

UPDATE analytics.forward_pass_shadow_policy_v1 SET
 schedule_policy='{"scheduler_job_code":"FORWARD_PASS_SHADOW_OBSERVER","source":"analytics.system_job_schedule_v1"}'::jsonb,
 updated_at=clock_timestamp()
WHERE policy_code='FORWARD_PASS_SHADOW_V2';

GRANT SELECT,INSERT,UPDATE ON analytics.forward_pass_shadow_heartbeat_v1 TO alex;
GRANT SELECT ON analytics.system_job_schedule_v1 TO alex;
GRANT SELECT,INSERT,UPDATE ON analytics.system_job_run_v1 TO alex;
COMMIT;
