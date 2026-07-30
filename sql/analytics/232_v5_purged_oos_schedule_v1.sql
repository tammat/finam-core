BEGIN;

INSERT INTO analytics.system_job_schedule_v1(
    job_code,executor_code,enabled,interval_minutes,timezone_code,weekdays,
    window_start,window_end,priority,timeout_seconds,config_version
) VALUES (
    'V5_PURGED_OOS_WORKER','V5_PURGED_OOS_WORKER_V1',true,15,'Europe/Moscow',
    '[0,1,2,3,4,5,6]'::jsonb,time '00:00',time '23:59:59',68,120,'V5_PURGED_OOS_WORKER_V1'
)
ON CONFLICT(job_code) DO UPDATE SET
    executor_code=excluded.executor_code,enabled=true,interval_minutes=excluded.interval_minutes,
    timezone_code=excluded.timezone_code,weekdays=excluded.weekdays,
    window_start=excluded.window_start,window_end=excluded.window_end,
    priority=excluded.priority,timeout_seconds=excluded.timeout_seconds,
    config_version=excluded.config_version,updated_at=clock_timestamp();

COMMIT;
