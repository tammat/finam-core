BEGIN;

UPDATE analytics.system_job_run_v1 run
SET status_code='TIMEOUT',
    return_code=-2,
    finished_at=clock_timestamp(),
    stderr_tail=concat_ws(
        E'\n',nullif(run.stderr_tail,''),
        'SCHEDULER_RESTART_STALE_RUNNING_RECONCILED'
    )
FROM analytics.system_job_schedule_v1 schedule
WHERE run.job_code=schedule.job_code
  AND run.status_code='RUNNING'
  AND run.started_at < clock_timestamp()
      - ((schedule.timeout_seconds + 60) * interval '1 second');

COMMIT;
