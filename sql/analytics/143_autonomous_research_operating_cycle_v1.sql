BEGIN;

CREATE TABLE IF NOT EXISTS analytics.market_session_policy_v1 (
    weekday_iso integer PRIMARY KEY CHECK (weekday_iso BETWEEN 1 AND 7),
    enabled boolean NOT NULL,
    opens_at time NOT NULL,
    closes_at time NOT NULL,
    timezone_code text NOT NULL DEFAULT 'Europe/Moscow',
    source_version text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.market_session_policy_v1
    (weekday_iso,enabled,opens_at,closes_at,source_version)
VALUES
    (1,true,'07:00','23:50','MARKET_SESSION_POLICY_V1'),
    (2,true,'07:00','23:50','MARKET_SESSION_POLICY_V1'),
    (3,true,'07:00','23:50','MARKET_SESSION_POLICY_V1'),
    (4,true,'07:00','23:50','MARKET_SESSION_POLICY_V1'),
    (5,true,'07:00','23:50','MARKET_SESSION_POLICY_V1'),
    (6,false,'00:00','00:00','MARKET_SESSION_POLICY_V1'),
    (7,true,'10:00','19:00','MARKET_SESSION_POLICY_V1')
ON CONFLICT(weekday_iso) DO UPDATE SET
    enabled=excluded.enabled,opens_at=excluded.opens_at,closes_at=excluded.closes_at,
    timezone_code=excluded.timezone_code,source_version=excluded.source_version,
    updated_at=clock_timestamp();

CREATE TABLE IF NOT EXISTS analytics.market_open_readiness_v1 (
    check_id uuid PRIMARY KEY,
    checked_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    phase_code text NOT NULL CHECK (phase_code IN
        ('WAITING','QUOTES','SIGNALS','TRADES','RESEARCH','OOS')),
    status_code text NOT NULL CHECK (status_code IN ('WAITING','HEALTHY','ATTENTION','FAILED')),
    session_open boolean NOT NULL,
    quote_age_seconds integer,
    signal_age_seconds integer,
    fill_age_seconds integer,
    pending_signals integer NOT NULL DEFAULT 0,
    reason_code text NOT NULL,
    next_session_at timestamptz,
    source_version text NOT NULL
);
CREATE INDEX IF NOT EXISTS market_open_readiness_latest_v1
ON analytics.market_open_readiness_v1(checked_at DESC);

CREATE TABLE IF NOT EXISTS analytics.historical_edge_audit_schedule_state_v1 (
    scheduler_code text PRIMARY KEY,
    status_code text NOT NULL CHECK(status_code IN ('NEVER_RUN','HEALTHY','FAILED')),
    decision_code text NOT NULL,
    request_id text,
    last_attempt_at timestamptz,
    last_enqueued_at timestamptz,
    last_error_code text,
    source_version text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
INSERT INTO analytics.historical_edge_audit_schedule_state_v1
    (scheduler_code,status_code,decision_code,source_version)
VALUES('HISTORICAL_EDGE_AUDIT','NEVER_RUN','NOT_RUN','HISTORICAL_EDGE_AUDIT_ENQUEUE_V1')
ON CONFLICT(scheduler_code) DO NOTHING;

INSERT INTO analytics.system_job_schedule_v1 VALUES
 ('MARKET_OPEN_READINESS_WEEKDAY','MARKET_OPEN_READINESS_V1',true,'Europe/Moscow',
  '[0,1,2,3,4]'::jsonb,'06:45','10:30',5,45,3,'V1',clock_timestamp()),
 ('MARKET_OPEN_READINESS_SUNDAY','MARKET_OPEN_READINESS_V1',true,'Europe/Moscow',
  '[6]'::jsonb,'09:45','11:30',5,45,3,'V1',clock_timestamp()),
 ('HISTORICAL_EDGE_AUDIT_NIGHT','HISTORICAL_EDGE_AUDIT_ENQUEUE_V1',true,'Europe/Moscow',
  '[0,1,2,3,4,5,6]'::jsonb,'00:10','06:30',1440,60,34,'V1_STRICT',clock_timestamp())
ON CONFLICT(job_code) DO UPDATE SET
 executor_code=excluded.executor_code,enabled=true,timezone_code=excluded.timezone_code,
 weekdays=excluded.weekdays,window_start=excluded.window_start,window_end=excluded.window_end,
 interval_minutes=excluded.interval_minutes,timeout_seconds=excluded.timeout_seconds,
 priority=excluded.priority,config_version=excluded.config_version,updated_at=clock_timestamp();

GRANT SELECT ON analytics.market_session_policy_v1,
    analytics.market_open_readiness_v1,
    analytics.historical_edge_audit_schedule_state_v1 TO alex,finam;
GRANT INSERT,UPDATE ON analytics.market_open_readiness_v1,
    analytics.historical_edge_audit_schedule_state_v1 TO alex,finam;

COMMIT;
