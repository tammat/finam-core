BEGIN;

CREATE TABLE IF NOT EXISTS analytics.paper_fill_anomaly_quarantine_v1(
    anomaly_key text PRIMARY KEY,
    symbol text NOT NULL,
    side text CHECK(side IS NULL OR side IN ('BUY','SELL')),
    range_start timestamptz NOT NULL,
    range_end timestamptz NOT NULL CHECK(range_end>range_start),
    fill_count integer NOT NULL CHECK(fill_count>0),
    reason_code text NOT NULL,
    detection_source text NOT NULL,
    enabled boolean NOT NULL DEFAULT true,
    detected_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS paper_fill_anomaly_quarantine_lookup_v1_idx
ON analytics.paper_fill_anomaly_quarantine_v1(symbol,range_start,range_end)
WHERE enabled;

INSERT INTO analytics.paper_fill_anomaly_quarantine_v1(
    anomaly_key,symbol,side,range_start,range_end,fill_count,reason_code,detection_source)
VALUES(
    'NGK6_20260506_ONE_SIDED_STORM','NGK6@RTSX','SELL',
    timestamptz '2026-05-06 10:54:59.688540 Europe/Moscow',
    timestamptz '2026-05-06 18:54:57.170867 Europe/Moscow',
    11861,'ONE_SIDED_UNLINKED_FILL_STORM','AUDITED_INCIDENT_20260506'
)
ON CONFLICT(anomaly_key) DO UPDATE SET
    fill_count=excluded.fill_count,
    reason_code=excluded.reason_code,
    enabled=true,
    updated_at=clock_timestamp();

GRANT SELECT ON analytics.paper_fill_anomaly_quarantine_v1 TO alex,finam;
GRANT INSERT,UPDATE ON analytics.paper_fill_anomaly_quarantine_v1 TO alex,finam;

INSERT INTO analytics.system_job_schedule_v1(
    job_code,executor_code,enabled,interval_minutes,timezone_code,weekdays,
    window_start,window_end,priority,timeout_seconds,config_version)
VALUES(
    'PAPER_FILL_ANOMALY_DETECTOR','PAPER_FILL_ANOMALY_DETECTOR_V1',true,
    5,'Europe/Moscow','[0,1,2,3,4,5,6]'::jsonb,time '00:00',time '23:59',
    2,30,'PAPER_FILL_ANOMALY_DETECTOR_V1'
)
ON CONFLICT(job_code) DO UPDATE SET
    executor_code=excluded.executor_code,enabled=true,
    interval_minutes=excluded.interval_minutes,timezone_code=excluded.timezone_code,
    weekdays=excluded.weekdays,window_start=excluded.window_start,
    window_end=excluded.window_end,priority=excluded.priority,
    timeout_seconds=excluded.timeout_seconds,config_version=excluded.config_version,
    updated_at=clock_timestamp();

COMMIT;
