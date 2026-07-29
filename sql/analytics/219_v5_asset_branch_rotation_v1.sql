BEGIN;

CREATE TABLE IF NOT EXISTS analytics.v5_asset_branch_rotation_v1(
    asset_code text PRIMARY KEY CHECK(asset_code IN ('USD','GOLD','CNY')),
    symbol text NOT NULL,
    previous_timeframe text NOT NULL CHECK(previous_timeframe IN ('M1','M5')),
    selected_timeframe text NOT NULL CHECK(selected_timeframe IN ('M1','M5')),
    reason_code text NOT NULL,
    last_switched_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.system_job_schedule_v1(
 job_code,executor_code,enabled,timezone_code,weekdays,window_start,window_end,
 interval_minutes,timeout_seconds,priority,config_version
) VALUES(
 'V5_ASSET_BRANCH_ROTATION','V5_ASSET_BRANCH_ROTATION_V1',true,
 'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,'00:00','23:59',5,60,7,
 'V5_ASSET_BRANCH_ROTATION_V1'
) ON CONFLICT(job_code) DO UPDATE SET executor_code=excluded.executor_code,
 enabled=true,interval_minutes=excluded.interval_minutes,timeout_seconds=excluded.timeout_seconds,
 priority=excluded.priority,config_version=excluded.config_version,updated_at=clock_timestamp();

GRANT SELECT,INSERT,UPDATE ON analytics.v5_asset_branch_rotation_v1 TO alex,finam;

COMMIT;
