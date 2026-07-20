BEGIN;

INSERT INTO analytics.system_job_schedule_v1
    (job_code, executor_code, enabled, timezone_code, weekdays, window_start, window_end,
     interval_minutes, timeout_seconds, priority, config_version)
VALUES
    ('WALKFORWARD_RESUME_MORNING', 'CHECKPOINTED_WALKFORWARD_V4', true, 'Europe/Moscow',
     '[0,1,2,3,4]'::jsonb, time '00:05', time '09:45', 10, 90, 65, 'V1_CHECKPOINT_45S'),
    ('WALKFORWARD_RESUME_EVENING', 'CHECKPOINTED_WALKFORWARD_V4', true, 'Europe/Moscow',
     '[0,1,2,3,4]'::jsonb, time '19:10', time '23:55', 10, 90, 65, 'V1_CHECKPOINT_45S'),
    ('WALKFORWARD_RESUME_WEEKEND', 'CHECKPOINTED_WALKFORWARD_V4', true, 'Europe/Moscow',
     '[5,6]'::jsonb, time '00:05', time '23:55', 10, 90, 65, 'V1_CHECKPOINT_45S')
ON CONFLICT (job_code) DO UPDATE SET
    executor_code = EXCLUDED.executor_code,
    enabled = EXCLUDED.enabled,
    timezone_code = EXCLUDED.timezone_code,
    weekdays = EXCLUDED.weekdays,
    window_start = EXCLUDED.window_start,
    window_end = EXCLUDED.window_end,
    interval_minutes = EXCLUDED.interval_minutes,
    timeout_seconds = EXCLUDED.timeout_seconds,
    priority = EXCLUDED.priority,
    config_version = EXCLUDED.config_version,
    updated_at = clock_timestamp();

COMMIT;
