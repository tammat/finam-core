INSERT INTO analytics.system_job_schedule_v1
(job_code,executor_code,enabled,interval_minutes,timezone_code,weekdays,window_start,window_end,priority,timeout_seconds,config_version)
VALUES ('EDGE_SEARCH_COMMAND_QUEUE','EDGE_SEARCH_COMMAND_QUEUE_V1',true,15,'Europe/Moscow',
        '[0,1,2,3,4,5,6]'::jsonb,time '00:00',time '08:59',40,3600,'V1_DB_SCHEDULED')
ON CONFLICT(job_code) DO UPDATE SET executor_code=EXCLUDED.executor_code,enabled=true,
interval_minutes=EXCLUDED.interval_minutes,weekdays=EXCLUDED.weekdays,
window_start=EXCLUDED.window_start,window_end=EXCLUDED.window_end,
priority=EXCLUDED.priority,timeout_seconds=EXCLUDED.timeout_seconds,
config_version=EXCLUDED.config_version,updated_at=clock_timestamp();
