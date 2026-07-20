BEGIN;

INSERT INTO analytics.system_job_schedule_v1
 (job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
  interval_minutes,timeout_seconds,priority,config_version)
VALUES
 ('SIGNAL_FUNNEL_HOURLY','SIGNAL_FUNNEL_ANALYTICS_V1',true,'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,time '00:00',time '23:59',60,300,45,'V1'),
 ('SIGNAL_FUNNEL_REASONS_HOURLY','SIGNAL_FUNNEL_REASON_ANALYTICS_V1',true,'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,time '00:00',time '23:59',60,600,46,'V1'),
 ('MODEL_HEALTH_HOURLY','MODEL_HEALTH_ENGINE_V1',true,'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,time '00:00',time '23:59',60,600,47,'V1')
ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,enabled=true,
 interval_minutes=excluded.interval_minutes,timeout_seconds=excluded.timeout_seconds,
 priority=excluded.priority,config_version=excluded.config_version,updated_at=clock_timestamp();

COMMIT;
