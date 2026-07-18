BEGIN;
INSERT INTO analytics.system_job_schedule_v1
 (job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
  interval_minutes,timeout_seconds,priority,config_version)
VALUES
 ('SWING_BARS_REFRESH_NIGHT','SWING_BARS_REFRESH_V1',true,'Europe/Moscow','[0,1,2,3,4]'::jsonb,
  time '00:15',time '08:30',60,1200,44,'V1_INCREMENTAL'),
 ('SWING_BARS_REFRESH_WEEKEND','SWING_BARS_REFRESH_V1',true,'Europe/Moscow','[5,6]'::jsonb,
  time '00:00',time '23:59',240,1200,44,'V1_INCREMENTAL')
ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,enabled=true,
 timezone_code=excluded.timezone_code,weekdays=excluded.weekdays,window_start=excluded.window_start,
 window_end=excluded.window_end,interval_minutes=excluded.interval_minutes,
 timeout_seconds=excluded.timeout_seconds,priority=excluded.priority,
 config_version=excluded.config_version,updated_at=clock_timestamp();
COMMIT;
