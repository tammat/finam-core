BEGIN;

CREATE TABLE IF NOT EXISTS analytics.paper_safety_monitor_v1(
    worker_code text PRIMARY KEY,
    status_code text NOT NULL CHECK(status_code IN ('NEVER_RUN','RUNNING','HEALTHY','ALERT','FAILED')),
    last_started_at timestamptz,
    last_success_at timestamptz,
    last_failure_at timestamptz,
    broker_positions integer NOT NULL DEFAULT 0,
    breaches integer NOT NULL DEFAULT 0,
    last_error text,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.paper_safety_monitor_v1(worker_code,status_code)
VALUES('PAPER_SAFETY_MONITOR_V1','NEVER_RUN')
ON CONFLICT(worker_code) DO NOTHING;

GRANT SELECT,INSERT,UPDATE ON analytics.paper_safety_monitor_v1 TO alex,finam;

COMMIT;
