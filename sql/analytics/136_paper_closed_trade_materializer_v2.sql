BEGIN;

CREATE TABLE IF NOT EXISTS analytics.paper_closed_trade_identity_v2(
    materialized_trade_id text PRIMARY KEY,
    entry_fill_id text NOT NULL,
    exit_fill_id text NOT NULL,
    claimed_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

GRANT SELECT,INSERT ON analytics.paper_closed_trade_identity_v2 TO alex,finam;

INSERT INTO analytics.system_job_schedule_v1(
    job_code,executor_code,enabled,interval_minutes,timezone_code,weekdays,
    window_start,window_end,priority,timeout_seconds,config_version)
VALUES(
    'PAPER_CLOSED_TRADE_MATERIALIZER','PAPER_CLOSED_TRADE_MATERIALIZER_V2',true,
    2,'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,time '00:00',time '23:59',
    1,50,'PAPER_CLOSED_TRADE_MATERIALIZER_V2'
)
ON CONFLICT(job_code) DO UPDATE SET
    executor_code=excluded.executor_code,
    enabled=true,
    interval_minutes=excluded.interval_minutes,
    timezone_code=excluded.timezone_code,
    weekdays=excluded.weekdays,
    window_start=excluded.window_start,
    window_end=excluded.window_end,
    priority=excluded.priority,
    timeout_seconds=excluded.timeout_seconds,
    config_version=excluded.config_version,
    updated_at=clock_timestamp();

COMMIT;
