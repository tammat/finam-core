CREATE UNIQUE INDEX IF NOT EXISTS command_request_v2_one_active_edge_search_idx
ON marketcore_action.command_request_v2(request_kind)
WHERE request_kind='EDGE_SEARCH_RUN' AND status IN ('PENDING','RUNNING');

INSERT INTO analytics.system_job_schedule_v1
(job_code,executor_code,enabled,interval_minutes,timezone_code,weekdays,window_start,window_end,priority,timeout_seconds,config_version)
VALUES ('EDGE_SEARCH_QUEUE_MONITOR','EDGE_SEARCH_QUEUE_MONITOR_V1',true,5,'Europe/Moscow',
        '[0,1,2,3,4,5,6]'::jsonb,time '00:00',time '23:59',6,60,'V1_DB_SCHEDULED')
ON CONFLICT(job_code) DO UPDATE SET executor_code=EXCLUDED.executor_code,enabled=true,
interval_minutes=EXCLUDED.interval_minutes,priority=EXCLUDED.priority,
timeout_seconds=EXCLUDED.timeout_seconds,config_version=EXCLUDED.config_version,updated_at=clock_timestamp();
