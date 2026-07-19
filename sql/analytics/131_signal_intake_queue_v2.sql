BEGIN;

CREATE TABLE IF NOT EXISTS analytics.signal_intake_policy_v2(
    policy_code text PRIMARY KEY,
    enabled boolean NOT NULL DEFAULT true,
    batch_size integer NOT NULL CHECK(batch_size BETWEEN 1 AND 1000),
    retry_seconds integer NOT NULL CHECK(retry_seconds BETWEEN 10 AND 3600),
    stale_running_minutes integer NOT NULL CHECK(stale_running_minutes BETWEEN 1 AND 1440),
    max_attempts integer NOT NULL CHECK(max_attempts BETWEEN 1 AND 100),
    priority_rules jsonb NOT NULL CHECK(jsonb_typeof(priority_rules)='object'),
    activated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    config_version text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.signal_intake_policy_v2(
    policy_code,batch_size,retry_seconds,stale_running_minutes,max_attempts,
    priority_rules,config_version)
VALUES (
    'DEFAULT',100,60,10,20,
    '{"LIVE":10,"PAPER":15,"INTRADAY":20,"SWING":30,"RESEARCH":60,"DEFAULT":50}'::jsonb,
    'SIGNAL_INTAKE_QUEUE_V2'
)
ON CONFLICT(policy_code) DO UPDATE SET
    enabled=true,batch_size=excluded.batch_size,retry_seconds=excluded.retry_seconds,
    stale_running_minutes=excluded.stale_running_minutes,max_attempts=excluded.max_attempts,
    priority_rules=excluded.priority_rules,config_version=excluded.config_version,
    updated_at=clock_timestamp();

CREATE TABLE IF NOT EXISTS analytics.signal_intake_queue_v2(
    signal_row_id bigint PRIMARY KEY REFERENCES public.signals(id) ON DELETE CASCADE,
    signal_id text NOT NULL,
    priority integer NOT NULL CHECK(priority BETWEEN 1 AND 100),
    status_code text NOT NULL DEFAULT 'QUEUED'
        CHECK(status_code IN ('QUEUED','RUNNING','WAITING','COMPLETE','FAILED')),
    attempts integer NOT NULL DEFAULT 0 CHECK(attempts >= 0),
    next_attempt_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    outcome_code text,
    failure_code text,
    enqueued_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    started_at timestamptz,
    finished_at timestamptz,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE UNIQUE INDEX IF NOT EXISTS signal_intake_queue_v2_signal_id_uidx
    ON analytics.signal_intake_queue_v2(signal_id);
CREATE INDEX IF NOT EXISTS signal_intake_queue_v2_pending_idx
    ON analytics.signal_intake_queue_v2(priority,next_attempt_at,enqueued_at)
    WHERE status_code IN ('QUEUED','WAITING');

CREATE OR REPLACE FUNCTION analytics.signal_intake_priority_v2(
    p_horizon text,p_strategy text,p_payload jsonb)
RETURNS integer LANGUAGE sql STABLE AS $$
    SELECT coalesce((p.priority_rules->>CASE
        WHEN upper(coalesce(p_payload->>'mode',''))='LIVE' THEN 'LIVE'
        WHEN upper(coalesce(p_payload->>'mode','')) IN ('PAPER','SHADOW') THEN 'PAPER'
        WHEN upper(coalesce(p_strategy,'')) LIKE 'HISTORICAL%%'
          OR upper(coalesce(p_payload->>'source','')) LIKE '%%REPLAY%%' THEN 'RESEARCH'
        WHEN upper(coalesce(p_horizon,''))='INTRADAY' THEN 'INTRADAY'
        WHEN upper(coalesce(p_horizon,''))='SWING' THEN 'SWING'
        ELSE 'DEFAULT' END)::integer,50)
    FROM analytics.signal_intake_policy_v2 p
    WHERE p.enabled ORDER BY p.updated_at DESC LIMIT 1
$$;

CREATE OR REPLACE FUNCTION analytics.enqueue_signal_intake_v2()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO analytics.signal_intake_queue_v2(signal_row_id,signal_id,priority)
    VALUES(
        NEW.id,
        coalesce(nullif(NEW.signal_id,''),'signal-row:'||NEW.id::text),
        analytics.signal_intake_priority_v2(NEW.horizon,NEW.strategy,NEW.payload)
    )
    ON CONFLICT DO NOTHING;
    RETURN NEW;
END $$;

DROP TRIGGER IF EXISTS signal_intake_enqueue_v2 ON public.signals;
CREATE TRIGGER signal_intake_enqueue_v2
AFTER INSERT ON public.signals
FOR EACH ROW EXECUTE FUNCTION analytics.enqueue_signal_intake_v2();

INSERT INTO analytics.system_job_schedule_v1(
    job_code,executor_code,enabled,interval_minutes,timezone_code,weekdays,
    window_start,window_end,priority,timeout_seconds,config_version)
VALUES (
    'SIGNAL_INTAKE_QUEUE','SIGNAL_INTAKE_QUEUE_V2',true,1,'Europe/Moscow',
    '[0,1,2,3,4,5,6]'::jsonb,time '00:00',time '23:59',3,55,'V2_DB_DRIVEN'
)
ON CONFLICT(job_code) DO UPDATE SET
    executor_code=excluded.executor_code,enabled=true,
    interval_minutes=excluded.interval_minutes,timezone_code=excluded.timezone_code,
    weekdays=excluded.weekdays,window_start=excluded.window_start,
    window_end=excluded.window_end,priority=excluded.priority,
    timeout_seconds=excluded.timeout_seconds,config_version=excluded.config_version,
    updated_at=clock_timestamp();

GRANT SELECT ON analytics.signal_intake_policy_v2 TO alex;
GRANT SELECT,INSERT,UPDATE ON analytics.signal_intake_queue_v2 TO alex;
GRANT USAGE ON SCHEMA analytics TO finam;
GRANT SELECT ON analytics.signal_intake_policy_v2 TO finam;
GRANT SELECT,INSERT,UPDATE ON analytics.signal_intake_queue_v2 TO finam;

COMMIT;
