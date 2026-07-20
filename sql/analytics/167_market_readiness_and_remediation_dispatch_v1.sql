BEGIN;

UPDATE analytics.system_job_schedule_v1
SET window_start=time '06:45',window_end=time '23:55',interval_minutes=5,
    config_version='MARKET_OPEN_READINESS_V2_TIMEFRAME_AWARE',updated_at=clock_timestamp()
WHERE job_code='MARKET_OPEN_READINESS_WEEKDAY';

UPDATE analytics.system_job_schedule_v1
SET window_start=time '09:45',window_end=time '19:15',interval_minutes=5,
    config_version='MARKET_OPEN_READINESS_V2_TIMEFRAME_AWARE',updated_at=clock_timestamp()
WHERE job_code='MARKET_OPEN_READINESS_SUNDAY';

COMMIT;
