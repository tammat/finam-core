BEGIN;

CREATE TABLE IF NOT EXISTS analytics.edge_search_auto_schedule_state_v1 (
    scheduler_code text PRIMARY KEY,
    status_code text NOT NULL CHECK(status_code IN ('NEVER_RUN','HEALTHY','FAILED')),
    decision_code text NOT NULL,
    market_data_watermark timestamptz,
    evaluated_watermark timestamptz,
    request_id text,
    source_version text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
INSERT INTO analytics.edge_search_auto_schedule_state_v1
  (scheduler_code,status_code,decision_code,source_version)
VALUES('EDGE_SEARCH_AUTO','NEVER_RUN','NOT_EVALUATED','EDGE_SEARCH_AUTO_ENQUEUE_V1')
ON CONFLICT(scheduler_code) DO NOTHING;

INSERT INTO analytics.system_job_schedule_v1
(job_code,executor_code,enabled,interval_minutes,timezone_code,weekdays,
 window_start,window_end,priority,timeout_seconds,config_version)
VALUES
('EDGE_SEARCH_AUTO_NIGHT','EDGE_SEARCH_AUTO_ENQUEUE_V1',true,60,'Europe/Moscow',
 '[0,1,2,3,4]'::jsonb,time '00:00',time '08:59',35,60,'V1_LOW_LOAD'),
('EDGE_SEARCH_AUTO_WEEKEND','EDGE_SEARCH_AUTO_ENQUEUE_V1',true,60,'Europe/Moscow',
 '[5,6]'::jsonb,time '00:00',time '23:59',35,60,'V1_LOW_LOAD')
ON CONFLICT(job_code) DO UPDATE SET
 executor_code=EXCLUDED.executor_code,enabled=true,interval_minutes=EXCLUDED.interval_minutes,
 timezone_code=EXCLUDED.timezone_code,weekdays=EXCLUDED.weekdays,
 window_start=EXCLUDED.window_start,window_end=EXCLUDED.window_end,
 priority=EXCLUDED.priority,timeout_seconds=EXCLUDED.timeout_seconds,
 config_version=EXCLUDED.config_version,updated_at=clock_timestamp();

GRANT SELECT,INSERT,UPDATE ON analytics.edge_search_auto_schedule_state_v1 TO alex;
COMMIT;
