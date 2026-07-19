BEGIN;

CREATE TABLE IF NOT EXISTS analytics.broker_position_sync_state_v1(
    worker_code text PRIMARY KEY,
    status_code text NOT NULL CHECK(status_code IN ('NEVER_RUN','HEALTHY','FAILED')),
    last_attempt_at timestamptz,
    last_success_at timestamptz,
    last_failure_at timestamptz,
    positions_scanned integer NOT NULL DEFAULT 0,
    positions_changed integer NOT NULL DEFAULT 0,
    positions_zeroed integer NOT NULL DEFAULT 0,
    last_error text,
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

INSERT INTO analytics.broker_position_sync_state_v1(worker_code,status_code)
VALUES('FINAM_POSITION_SYNC','NEVER_RUN') ON CONFLICT(worker_code) DO NOTHING;

GRANT SELECT,INSERT,UPDATE ON analytics.broker_position_sync_state_v1 TO alex,finam;

COMMIT;
