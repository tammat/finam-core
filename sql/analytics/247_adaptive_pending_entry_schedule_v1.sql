INSERT INTO analytics.system_job_schedule_v1(
  job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
  interval_minutes,timeout_seconds,priority,config_version)
VALUES('ADAPTIVE_PENDING_ENTRY','ADAPTIVE_PENDING_ENTRY_V1',true,'Europe/Moscow',
       '[0,1,2,3,4,5,6]'::jsonb,'00:00','23:59',1,45,1,'ADAPTIVE_PENDING_ENTRY_V1')
ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,
  enabled=excluded.enabled,weekdays=excluded.weekdays,window_start=excluded.window_start,
  window_end=excluded.window_end,interval_minutes=excluded.interval_minutes,
  timeout_seconds=excluded.timeout_seconds,priority=excluded.priority,
  config_version=excluded.config_version,updated_at=clock_timestamp();
