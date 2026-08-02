BEGIN;

-- Equity bars warm from 06:00. Evidence workers must be ready before 06:50.
WITH previous AS (
    SELECT job_code, to_jsonb(s) AS schedule
    FROM analytics.system_job_schedule_v1 s
    WHERE job_code IN (
        'FORWARD_PASS_SHADOW_OBSERVER',
        'SHADOW_PIPELINE_MONITOR',
        'SHADOW_PASS_EVALUATOR'
    )
), changed AS (
    UPDATE analytics.system_job_schedule_v1 s
    SET window_start = time '06:40',
        updated_at = clock_timestamp(),
        config_version = 'V2_EQUITY_MORNING_SESSION'
    FROM previous p
    WHERE s.job_code = p.job_code
    RETURNING s.job_code, p.schedule AS previous_schedule, to_jsonb(s) AS new_schedule
)
INSERT INTO analytics.system_job_schedule_change_audit_v1(
    changed_at, job_code, previous_schedule, new_schedule, reason_code
)
SELECT clock_timestamp(), job_code, previous_schedule, new_schedule,
       'EQUITY_MORNING_SESSION_STARTS_0650'
FROM changed
WHERE NOT EXISTS (
    SELECT 1 FROM analytics.system_job_schedule_change_audit_v1 a
    WHERE a.job_code = changed.job_code
      AND a.reason_code = 'EQUITY_MORNING_SESSION_STARTS_0650'
);

COMMIT;
